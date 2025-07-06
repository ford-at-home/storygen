"""
Repository pattern implementation for data access
Provides CRUD operations and complex queries for all entities
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import logging
from decimal import Decimal
from abc import ABC, abstractmethod
import time

from .models import (
    User, Story, Template, RichmondContent, Analytics,
    UserRole, StoryStyle, StoryStatus, TemplateCategory
)
from .dynamodb_schema import DynamoDBTables, DynamoDBKeyBuilder
from session_manager import Session, SessionStatus, ConversationStage

logger = logging.getLogger('storygen.repository')


class BaseRepository(ABC):
    """Base repository with common DynamoDB operations"""
    
    def __init__(self, table_name: str, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        self.dynamodb = boto3.resource('dynamodb', region_name=region, endpoint_url=endpoint_url)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
    
    def _serialize_item(self, item: Dict) -> Dict:
        """Convert Python types to DynamoDB-compatible types"""
        def serialize_value(v):
            if isinstance(v, float):
                return Decimal(str(v))
            elif isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, dict):
                return {k: serialize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [serialize_value(val) for val in v]
            return v
        
        return {k: serialize_value(v) for k, v in item.items() if v is not None}
    
    def _deserialize_item(self, item: Dict) -> Dict:
        """Convert DynamoDB types back to Python types"""
        def deserialize_value(v):
            if isinstance(v, Decimal):
                return float(v)
            elif isinstance(v, dict):
                return {k: deserialize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [deserialize_value(val) for val in v]
            return v
        
        return {k: deserialize_value(v) for k, v in item.items()}
    
    def _batch_write_items(self, items: List[Dict], batch_size: int = 25):
        """Write items in batches"""
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            with self.table.batch_writer() as batch_writer:
                for item in batch:
                    batch_writer.put_item(Item=self._serialize_item(item))
    
    def _paginate_query(self, **kwargs) -> List[Dict]:
        """Execute paginated query"""
        items = []
        response = self.table.query(**kwargs)
        items.extend(response.get('Items', []))
        
        while 'LastEvaluatedKey' in response:
            kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = self.table.query(**kwargs)
            items.extend(response.get('Items', []))
        
        return [self._deserialize_item(item) for item in items]
    
    @abstractmethod
    def save(self, entity: Any) -> bool:
        """Save entity to database"""
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity"""
        pass


class UserRepository(BaseRepository):
    """Repository for User entities"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.MAIN_TABLE, region, endpoint_url)
    
    def save(self, user: User) -> bool:
        """Save user to database"""
        try:
            user.updated_at = datetime.utcnow()
            
            # Build item with keys
            item = user.to_dict()
            item.update(DynamoDBKeyBuilder.user_key(user.user_id))
            item['entity_type'] = DynamoDBTables.ENTITY_USER
            
            # Add GSI keys
            item.update(DynamoDBKeyBuilder.type_status_gsi(
                DynamoDBTables.ENTITY_USER,
                user.role.value,
                user.created_at
            ))
            
            # Save to database
            self.table.put_item(Item=self._serialize_item(item))
            logger.info(f"Saved user {user.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user {user.user_id}: {e}")
            return False
    
    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            response = self.table.get_item(
                Key=DynamoDBKeyBuilder.user_key(user_id)
            )
            
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return User.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (requires scan - consider GSI for production)"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('email').eq(email) & Attr('entity_type').eq(DynamoDBTables.ENTITY_USER)
            )
            
            items = response.get('Items', [])
            if items:
                item = self._deserialize_item(items[0])
                return User.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('username').eq(username) & Attr('entity_type').eq(DynamoDBTables.ENTITY_USER)
            )
            
            items = response.get('Items', [])
            if items:
                item = self._deserialize_item(items[0])
                return User.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    def list_by_role(self, role: UserRole, limit: int = 100) -> List[User]:
        """List users by role"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_TYPE_STATUS,
                KeyConditionExpression=Key('gsi2pk').eq(f"{DynamoDBTables.ENTITY_USER}#{role.value}"),
                Limit=limit
            )
            
            return [User.from_dict(item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to list users by role {role}: {e}")
            return []
    
    def update_stats(self, user_id: str, stat_updates: Dict[str, int]) -> bool:
        """Update user statistics atomically"""
        try:
            update_expr = "SET updated_at = :updated"
            expr_values = {":updated": datetime.utcnow().isoformat()}
            
            # Build update expression for stats
            for stat, increment in stat_updates.items():
                update_expr += f", stats.{stat} = stats.{stat} + :inc_{stat}"
                expr_values[f":inc_{stat}"] = increment
            
            self.table.update_item(
                Key=DynamoDBKeyBuilder.user_key(user_id),
                UpdateExpression=update_expr,
                ExpressionAttributeValues=self._serialize_item(expr_values)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update stats for user {user_id}: {e}")
            return False
    
    def delete(self, user_id: str) -> bool:
        """Delete user (soft delete by updating status)"""
        try:
            # Instead of hard delete, update role to indicate deletion
            self.table.update_item(
                Key=DynamoDBKeyBuilder.user_key(user_id),
                UpdateExpression="SET #role = :deleted, updated_at = :updated",
                ExpressionAttributeNames={"#role": "role"},
                ExpressionAttributeValues={
                    ":deleted": "deleted",
                    ":updated": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Soft deleted user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False


class SessionRepository(BaseRepository):
    """Repository for Session entities"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.MAIN_TABLE, region, endpoint_url)
    
    def save(self, session: Session) -> bool:
        """Save session to database"""
        try:
            # Save session metadata
            session_dict = session.to_dict()
            item = {
                **session_dict,
                **DynamoDBKeyBuilder.session_key(session.session_id),
                'entity_type': DynamoDBTables.ENTITY_SESSION
            }
            
            # Add GSI keys
            if session.user_id:
                item.update(DynamoDBKeyBuilder.user_session_gsi(session.user_id, session.session_id))
            
            item.update(DynamoDBKeyBuilder.type_status_gsi(
                DynamoDBTables.ENTITY_SESSION,
                session.status.value,
                session.created_at
            ))
            
            # Set TTL for session expiration (7 days)
            item['ttl'] = int((datetime.utcnow() + timedelta(days=7)).timestamp())
            
            # Save metadata
            self.table.put_item(Item=self._serialize_item(item))
            
            # Save conversation turns separately for efficient retrieval
            self._save_conversation_turns(session)
            
            logger.info(f"Saved session {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def _save_conversation_turns(self, session: Session):
        """Save conversation turns as separate items"""
        items = []
        for turn in session.conversation_history:
            item = {
                **turn.to_dict(),
                **DynamoDBKeyBuilder.session_turn_key(session.session_id, turn.turn),
                'entity_type': 'TURN',
                'session_id': session.session_id
            }
            items.append(item)
        
        if items:
            self._batch_write_items(items)
    
    def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            # Get session metadata
            response = self.table.get_item(
                Key=DynamoDBKeyBuilder.session_key(session_id)
            )
            
            if 'Item' not in response:
                return None
            
            item = self._deserialize_item(response['Item'])
            session = Session.from_dict(item)
            
            # Get conversation turns
            turns = self._get_conversation_turns(session_id)
            session.conversation_history = turns
            
            # Check if expired
            if session.is_expired():
                session.status = SessionStatus.EXPIRED
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def _get_conversation_turns(self, session_id: str) -> List[Any]:
        """Get all conversation turns for a session"""
        from session_manager import ConversationTurn
        
        items = self._paginate_query(
            KeyConditionExpression=Key('pk').eq(f"SESSION#{session_id}") & Key('sk').begins_with('TURN#')
        )
        
        turns = []
        for item in items:
            turn = ConversationTurn(
                item['turn'],
                item['stage'],
                item.get('user_input'),
                item.get('llm_response'),
                item.get('context_used', [])
            )
            turn.timestamp = item['timestamp']
            turns.append(turn)
        
        return sorted(turns, key=lambda t: t.turn)
    
    def get_user_sessions(self, user_id: str, status: Optional[SessionStatus] = None) -> List[Session]:
        """Get all sessions for a user"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_USER_SESSION,
                KeyConditionExpression=Key('gsi3pk').eq(f"USER#{user_id}")
            )
            
            sessions = []
            for item in items:
                if status and item.get('status') != status.value:
                    continue
                    
                # Get full session data
                session = self.get(item['session_id'])
                if session:
                    sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []
    
    def get_active_sessions(self, limit: int = 100) -> List[Session]:
        """Get all active sessions"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_TYPE_STATUS,
                KeyConditionExpression=Key('gsi2pk').eq(f"{DynamoDBTables.ENTITY_SESSION}#{SessionStatus.ACTIVE.value}"),
                Limit=limit
            )
            
            sessions = []
            for item in items:
                session = self.get(item['session_id'])
                if session and session.status == SessionStatus.ACTIVE:
                    sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """Update session status"""
        try:
            self.table.update_item(
                Key=DynamoDBKeyBuilder.session_key(session_id),
                UpdateExpression="SET #status = :status, updated_at = :updated",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": status.value,
                    ":updated": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id} status: {e}")
            return False
    
    def delete(self, session_id: str) -> bool:
        """Delete session and all related data"""
        try:
            # Delete session metadata
            self.table.delete_item(Key=DynamoDBKeyBuilder.session_key(session_id))
            
            # Delete all conversation turns
            turns = self._paginate_query(
                KeyConditionExpression=Key('pk').eq(f"SESSION#{session_id}") & Key('sk').begins_with('TURN#')
            )
            
            with self.table.batch_writer() as batch:
                for turn in turns:
                    batch.delete_item(Key={'pk': turn['pk'], 'sk': turn['sk']})
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False


class StoryRepository(BaseRepository):
    """Repository for Story entities"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.MAIN_TABLE, region, endpoint_url)
    
    def save(self, story: Story) -> bool:
        """Save story to database"""
        try:
            story.updated_at = datetime.utcnow()
            
            # Calculate metrics
            story.metrics['word_count'] = len(story.content.split())
            story.metrics['char_count'] = len(story.content)
            story.metrics['reading_time_minutes'] = round(story.metrics['word_count'] / 200, 1)
            
            # Build item
            item = story.to_dict()
            item.update(DynamoDBKeyBuilder.story_key(story.story_id))
            item['entity_type'] = DynamoDBTables.ENTITY_STORY
            
            # Add GSI keys
            if story.user_id:
                item.update(DynamoDBKeyBuilder.user_stories_gsi(story.user_id, story.created_at))
            
            item.update(DynamoDBKeyBuilder.type_status_gsi(
                DynamoDBTables.ENTITY_STORY,
                story.status.value,
                story.created_at
            ))
            
            # Save to database
            self.table.put_item(Item=self._serialize_item(item))
            
            # Save version if content changed
            if story.version > 1:
                self._save_story_version(story)
            
            logger.info(f"Saved story {story.story_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save story {story.story_id}: {e}")
            return False
    
    def _save_story_version(self, story: Story):
        """Save story version"""
        if story.versions:
            latest_version = story.versions[-1]
            item = {
                **latest_version,
                **DynamoDBKeyBuilder.story_version_key(story.story_id, latest_version['version']),
                'entity_type': 'STORY_VERSION',
                'story_id': story.story_id
            }
            self.table.put_item(Item=self._serialize_item(item))
    
    def get(self, story_id: str) -> Optional[Story]:
        """Get story by ID"""
        try:
            response = self.table.get_item(
                Key=DynamoDBKeyBuilder.story_key(story_id)
            )
            
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return Story.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get story {story_id}: {e}")
            return None
    
    def get_user_stories(self, user_id: str, status: Optional[StoryStatus] = None, 
                        limit: int = 50) -> List[Story]:
        """Get stories for a user"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_USER_CREATED,
                KeyConditionExpression=Key('gsi1pk').eq(f"USER#{user_id}") & Key('gsi1sk').begins_with('STORY#'),
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            stories = []
            for item in items:
                if status and item.get('status') != status.value:
                    continue
                stories.append(Story.from_dict(item))
            
            return stories
            
        except Exception as e:
            logger.error(f"Failed to get stories for user {user_id}: {e}")
            return []
    
    def get_by_session(self, session_id: str) -> Optional[Story]:
        """Get story by session ID"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('session_id').eq(session_id) & Attr('entity_type').eq(DynamoDBTables.ENTITY_STORY)
            )
            
            items = response.get('Items', [])
            if items:
                item = self._deserialize_item(items[0])
                return Story.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get story by session {session_id}: {e}")
            return None
    
    def get_story_versions(self, story_id: str) -> List[Dict]:
        """Get all versions of a story"""
        try:
            items = self._paginate_query(
                KeyConditionExpression=Key('pk').eq(f"STORY#{story_id}") & Key('sk').begins_with('VERSION#')
            )
            
            return sorted(items, key=lambda x: x['version'])
            
        except Exception as e:
            logger.error(f"Failed to get versions for story {story_id}: {e}")
            return []
    
    def update_status(self, story_id: str, status: StoryStatus) -> bool:
        """Update story status"""
        try:
            update_expr = "SET #status = :status, updated_at = :updated"
            expr_values = {
                ":status": status.value,
                ":updated": datetime.utcnow().isoformat()
            }
            
            # Add published_at if publishing
            if status == StoryStatus.PUBLISHED:
                update_expr += ", published_at = :published"
                expr_values[":published"] = datetime.utcnow().isoformat()
            
            self.table.update_item(
                Key=DynamoDBKeyBuilder.story_key(story_id),
                UpdateExpression=update_expr,
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=self._serialize_item(expr_values)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update story {story_id} status: {e}")
            return False
    
    def search_stories(self, query: str, user_id: Optional[str] = None, 
                      limit: int = 50) -> List[Story]:
        """Search stories by content (basic implementation)"""
        try:
            filter_expr = Attr('entity_type').eq(DynamoDBTables.ENTITY_STORY) & (
                Attr('content').contains(query) | 
                Attr('title').contains(query) |
                Attr('elements.core_idea').contains(query)
            )
            
            if user_id:
                filter_expr = filter_expr & Attr('user_id').eq(user_id)
            
            response = self.table.scan(
                FilterExpression=filter_expr,
                Limit=limit
            )
            
            stories = []
            for item in response.get('Items', []):
                item = self._deserialize_item(item)
                stories.append(Story.from_dict(item))
            
            return stories
            
        except Exception as e:
            logger.error(f"Failed to search stories: {e}")
            return []
    
    def delete(self, story_id: str) -> bool:
        """Delete story (soft delete)"""
        try:
            return self.update_status(story_id, StoryStatus.DELETED)
            
        except Exception as e:
            logger.error(f"Failed to delete story {story_id}: {e}")
            return False


class TemplateRepository(BaseRepository):
    """Repository for Template entities"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.MAIN_TABLE, region, endpoint_url)
    
    def save(self, template: Template) -> bool:
        """Save template to database"""
        try:
            template.updated_at = datetime.utcnow()
            
            # Build item
            item = template.to_dict()
            item.update(DynamoDBKeyBuilder.template_key(template.template_id))
            item['entity_type'] = DynamoDBTables.ENTITY_TEMPLATE
            
            # Add GSI for category queries
            item.update(DynamoDBKeyBuilder.type_status_gsi(
                DynamoDBTables.ENTITY_TEMPLATE,
                template.category.value,
                template.created_at
            ))
            
            # Save to database
            self.table.put_item(Item=self._serialize_item(item))
            
            logger.info(f"Saved template {template.template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template {template.template_id}: {e}")
            return False
    
    def get(self, template_id: str) -> Optional[Template]:
        """Get template by ID"""
        try:
            response = self.table.get_item(
                Key=DynamoDBKeyBuilder.template_key(template_id)
            )
            
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return Template.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            return None
    
    def list_by_category(self, category: TemplateCategory, limit: int = 50) -> List[Template]:
        """List templates by category"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_TYPE_STATUS,
                KeyConditionExpression=Key('gsi2pk').eq(f"{DynamoDBTables.ENTITY_TEMPLATE}#{category.value}"),
                Limit=limit
            )
            
            return [Template.from_dict(item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to list templates by category {category}: {e}")
            return []
    
    def list_public_templates(self, limit: int = 50) -> List[Template]:
        """List all public templates"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('entity_type').eq(DynamoDBTables.ENTITY_TEMPLATE) & Attr('is_public').eq(True),
                Limit=limit
            )
            
            templates = []
            for item in response.get('Items', []):
                item = self._deserialize_item(item)
                templates.append(Template.from_dict(item))
            
            return sorted(templates, key=lambda t: t.rating, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list public templates: {e}")
            return []
    
    def increment_usage(self, template_id: str) -> bool:
        """Increment template usage count"""
        try:
            self.table.update_item(
                Key=DynamoDBKeyBuilder.template_key(template_id),
                UpdateExpression="SET usage_count = usage_count + :inc, updated_at = :updated",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":updated": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to increment usage for template {template_id}: {e}")
            return False
    
    def update_rating(self, template_id: str, new_rating: float) -> bool:
        """Update template rating"""
        try:
            # Get current template to calculate new average
            template = self.get(template_id)
            if not template:
                return False
            
            # Calculate new average rating
            total_rating = template.rating * template.ratings_count
            new_ratings_count = template.ratings_count + 1
            new_average = (total_rating + new_rating) / new_ratings_count
            
            self.table.update_item(
                Key=DynamoDBKeyBuilder.template_key(template_id),
                UpdateExpression="SET rating = :rating, ratings_count = :count, updated_at = :updated",
                ExpressionAttributeValues={
                    ":rating": Decimal(str(new_average)),
                    ":count": new_ratings_count,
                    ":updated": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rating for template {template_id}: {e}")
            return False
    
    def delete(self, template_id: str) -> bool:
        """Delete template"""
        try:
            self.table.delete_item(Key=DynamoDBKeyBuilder.template_key(template_id))
            logger.info(f"Deleted template {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
            return False


class RichmondContentRepository(BaseRepository):
    """Repository for Richmond content entities"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.MAIN_TABLE, region, endpoint_url)
    
    def save(self, content: RichmondContent) -> bool:
        """Save Richmond content to database"""
        try:
            content.updated_at = datetime.utcnow()
            
            # Build item
            item = content.to_dict()
            item.update(DynamoDBKeyBuilder.content_key(content.content_id))
            item['entity_type'] = DynamoDBTables.ENTITY_CONTENT
            
            # Add GSI for content type queries
            item.update(DynamoDBKeyBuilder.content_type_gsi(
                content.content_type,
                content.created_at
            ))
            
            # Set TTL if content expires
            if content.expires_at:
                item['ttl'] = int(content.expires_at.timestamp())
            
            # Save to database
            self.table.put_item(Item=self._serialize_item(item))
            
            logger.info(f"Saved Richmond content {content.content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Richmond content {content.content_id}: {e}")
            return False
    
    def save_batch(self, contents: List[RichmondContent]) -> int:
        """Save multiple content items in batch"""
        items = []
        for content in contents:
            content.updated_at = datetime.utcnow()
            item = content.to_dict()
            item.update(DynamoDBKeyBuilder.content_key(content.content_id))
            item['entity_type'] = DynamoDBTables.ENTITY_CONTENT
            item.update(DynamoDBKeyBuilder.content_type_gsi(
                content.content_type,
                content.created_at
            ))
            if content.expires_at:
                item['ttl'] = int(content.expires_at.timestamp())
            items.append(item)
        
        self._batch_write_items(items)
        return len(items)
    
    def get(self, content_id: str) -> Optional[RichmondContent]:
        """Get content by ID"""
        try:
            response = self.table.get_item(
                Key=DynamoDBKeyBuilder.content_key(content_id)
            )
            
            if 'Item' in response:
                item = self._deserialize_item(response['Item'])
                return RichmondContent.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get content {content_id}: {e}")
            return None
    
    def get_by_embedding_id(self, embedding_id: str) -> Optional[RichmondContent]:
        """Get content by embedding ID"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('embedding_id').eq(embedding_id) & Attr('entity_type').eq(DynamoDBTables.ENTITY_CONTENT)
            )
            
            items = response.get('Items', [])
            if items:
                item = self._deserialize_item(items[0])
                return RichmondContent.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get content by embedding {embedding_id}: {e}")
            return None
    
    def list_by_type(self, content_type: str, limit: int = 100) -> List[RichmondContent]:
        """List content by type"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_CONTENT_TYPE,
                KeyConditionExpression=Key('gsi4pk').eq(f"CONTENT_TYPE#{content_type}"),
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            return [RichmondContent.from_dict(item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to list content by type {content_type}: {e}")
            return []
    
    def update_usage(self, content_id: str, relevance_score: float) -> bool:
        """Update content usage statistics"""
        try:
            self.table.update_item(
                Key=DynamoDBKeyBuilder.content_key(content_id),
                UpdateExpression="SET usage_count = usage_count + :inc, last_used = :last, relevance_scores = list_append(relevance_scores, :score)",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":last": datetime.utcnow().isoformat(),
                    ":score": [Decimal(str(relevance_score))]
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update usage for content {content_id}: {e}")
            return False
    
    def get_expired_content(self, limit: int = 100) -> List[RichmondContent]:
        """Get expired content for cleanup"""
        try:
            current_time = int(datetime.utcnow().timestamp())
            
            response = self.table.scan(
                FilterExpression=Attr('entity_type').eq(DynamoDBTables.ENTITY_CONTENT) & 
                                Attr('ttl').lt(current_time),
                Limit=limit
            )
            
            contents = []
            for item in response.get('Items', []):
                item = self._deserialize_item(item)
                contents.append(RichmondContent.from_dict(item))
            
            return contents
            
        except Exception as e:
            logger.error(f"Failed to get expired content: {e}")
            return []
    
    def delete(self, content_id: str) -> bool:
        """Delete content"""
        try:
            self.table.delete_item(Key=DynamoDBKeyBuilder.content_key(content_id))
            logger.info(f"Deleted content {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete content {content_id}: {e}")
            return False
    
    def delete_batch(self, content_ids: List[str]) -> int:
        """Delete multiple content items"""
        deleted = 0
        with self.table.batch_writer() as batch:
            for content_id in content_ids:
                try:
                    batch.delete_item(Key=DynamoDBKeyBuilder.content_key(content_id))
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete content {content_id}: {e}")
        
        return deleted


class AnalyticsRepository(BaseRepository):
    """Repository for Analytics events"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        super().__init__(DynamoDBTables.ANALYTICS_TABLE, region, endpoint_url)
    
    def save(self, event: Analytics) -> bool:
        """Save analytics event"""
        try:
            # Build item
            item = event.to_dict()
            
            # Set primary key based on user or session
            entity_id = event.user_id or event.session_id or "anonymous"
            item.update(DynamoDBKeyBuilder.analytics_key(entity_id, event.timestamp, event.event_id))
            
            # Add attributes for GSI
            item['event_type'] = event.event_type
            item['timestamp'] = event.timestamp.isoformat()
            
            # Save to database
            self.table.put_item(Item=self._serialize_item(item))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save analytics event {event.event_id}: {e}")
            return False
    
    def save_batch(self, events: List[Analytics]) -> int:
        """Save multiple analytics events"""
        items = []
        for event in events:
            item = event.to_dict()
            entity_id = event.user_id or event.session_id or "anonymous"
            item.update(DynamoDBKeyBuilder.analytics_key(entity_id, event.timestamp, event.event_id))
            item['event_type'] = event.event_type
            item['timestamp'] = event.timestamp.isoformat()
            items.append(item)
        
        self._batch_write_items(items)
        return len(items)
    
    def get(self, event_id: str) -> Optional[Analytics]:
        """Get analytics event by ID (requires scan)"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('event_id').eq(event_id)
            )
            
            items = response.get('Items', [])
            if items:
                item = self._deserialize_item(items[0])
                return Analytics.from_dict(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get analytics event {event_id}: {e}")
            return None
    
    def get_user_events(self, user_id: str, start_time: datetime, 
                       end_time: datetime) -> List[Analytics]:
        """Get analytics events for a user in time range"""
        try:
            items = self._paginate_query(
                KeyConditionExpression=Key('pk').eq(user_id) & 
                                     Key('sk').between(
                                         f"{start_time.isoformat()}#",
                                         f"{end_time.isoformat()}#z"
                                     )
            )
            
            return [Analytics.from_dict(item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get events for user {user_id}: {e}")
            return []
    
    def get_events_by_type(self, event_type: str, start_time: datetime, 
                          end_time: datetime, limit: int = 1000) -> List[Analytics]:
        """Get events by type in time range"""
        try:
            items = self._paginate_query(
                IndexName=DynamoDBTables.GSI_TIMESTAMP,
                KeyConditionExpression=Key('event_type').eq(event_type) & 
                                     Key('timestamp').between(
                                         start_time.isoformat(),
                                         end_time.isoformat()
                                     ),
                Limit=limit
            )
            
            return [Analytics.from_dict(item) for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get events by type {event_type}: {e}")
            return []
    
    def get_event_counts(self, event_type: str, start_time: datetime, 
                        end_time: datetime, interval: str = "hour") -> Dict[str, int]:
        """Get event counts aggregated by interval"""
        events = self.get_events_by_type(event_type, start_time, end_time)
        
        # Aggregate by interval
        counts = {}
        for event in events:
            if interval == "hour":
                key = event.timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "day":
                key = event.timestamp.strftime("%Y-%m-%d")
            elif interval == "week":
                key = event.timestamp.strftime("%Y-W%U")
            else:
                key = event.timestamp.strftime("%Y-%m")
            
            counts[key] = counts.get(key, 0) + 1
        
        return counts
    
    def get_funnel_metrics(self, user_id: str, funnel_steps: List[str], 
                          start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate funnel metrics for a user"""
        events = self.get_user_events(user_id, start_time, end_time)
        
        # Track completion of each step
        step_completed = {step: False for step in funnel_steps}
        step_times = {}
        
        for event in events:
            if event.event_type in funnel_steps and not step_completed[event.event_type]:
                step_completed[event.event_type] = True
                step_times[event.event_type] = event.timestamp
        
        # Calculate metrics
        completed_steps = sum(1 for completed in step_completed.values() if completed)
        conversion_rate = completed_steps / len(funnel_steps) if funnel_steps else 0
        
        return {
            "steps_completed": completed_steps,
            "total_steps": len(funnel_steps),
            "conversion_rate": conversion_rate,
            "step_status": step_completed,
            "step_times": step_times
        }
    
    def delete(self, event_id: str) -> bool:
        """Analytics events are typically not deleted"""
        logger.warning(f"Attempted to delete analytics event {event_id}")
        return False