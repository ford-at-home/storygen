"""
Data migration tools for seamless transition from in-memory to persistent storage
Handles data validation, transformation, and migration with rollback support
"""
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
import asyncio
from dataclasses import dataclass
import hashlib
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import User, Story, Session, Template, RichmondContent
from .repositories import (
    UserRepository, SessionRepository, StoryRepository,
    TemplateRepository, RichmondContentRepository
)
from .dynamodb_schema import DynamoDBManager, DynamoDBTables
from .cache import cache_manager, entity_cache
from .backup import BackupManager
from session_manager import session_store as in_memory_session_store

logger = logging.getLogger('storygen.migration')


@dataclass
class MigrationConfig:
    """Configuration for data migration"""
    # Migration settings
    batch_size: int = 100
    max_workers: int = 4
    dry_run: bool = False
    validate_data: bool = True
    create_backup: bool = True
    
    # Source settings
    source_type: str = "in_memory"  # in_memory, json_files, dynamodb_export
    source_path: Optional[str] = None
    
    # Target settings
    target_region: str = "us-east-1"
    create_tables: bool = True
    
    # Rollback settings
    enable_rollback: bool = True
    rollback_on_error: bool = True
    
    # Progress tracking
    checkpoint_interval: int = 1000
    checkpoint_file: str = "migration_checkpoint.json"


class MigrationValidator:
    """Validates data before and after migration"""
    
    def validate_user(self, user_data: Dict) -> Tuple[bool, List[str]]:
        """Validate user data"""
        errors = []
        
        # Required fields
        if not user_data.get("user_id"):
            errors.append("Missing user_id")
        
        # Email format
        email = user_data.get("email")
        if email and "@" not in email:
            errors.append(f"Invalid email format: {email}")
        
        # Role validation
        valid_roles = ["anonymous", "registered", "premium", "admin"]
        if user_data.get("role") not in valid_roles:
            errors.append(f"Invalid role: {user_data.get('role')}")
        
        # Date validation
        try:
            if user_data.get("created_at"):
                datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00"))
        except Exception:
            errors.append("Invalid created_at date format")
        
        return len(errors) == 0, errors
    
    def validate_session(self, session_data: Dict) -> Tuple[bool, List[str]]:
        """Validate session data"""
        errors = []
        
        # Required fields
        if not session_data.get("session_id"):
            errors.append("Missing session_id")
        
        # Status validation
        valid_statuses = ["active", "completed", "abandoned", "expired"]
        if session_data.get("status") not in valid_statuses:
            errors.append(f"Invalid status: {session_data.get('status')}")
        
        # Stage validation
        valid_stages = [
            "kickoff", "depth_analysis", "follow_up", "personal_anecdote",
            "hook_generation", "arc_development", "quote_integration",
            "cta_generation", "final_story"
        ]
        if session_data.get("current_stage") not in valid_stages:
            errors.append(f"Invalid stage: {session_data.get('current_stage')}")
        
        # Conversation history validation
        history = session_data.get("conversation_history", [])
        if not isinstance(history, list):
            errors.append("conversation_history must be a list")
        
        return len(errors) == 0, errors
    
    def validate_story(self, story_data: Dict) -> Tuple[bool, List[str]]:
        """Validate story data"""
        errors = []
        
        # Required fields
        if not story_data.get("story_id"):
            errors.append("Missing story_id")
        
        if not story_data.get("content"):
            errors.append("Missing story content")
        
        # Style validation
        valid_styles = ["short_post", "long_post", "blog_post", "thread", "newsletter"]
        if story_data.get("style") not in valid_styles:
            errors.append(f"Invalid style: {story_data.get('style')}")
        
        # Status validation
        valid_statuses = ["draft", "generating", "completed", "failed", "published"]
        if story_data.get("status") not in valid_statuses:
            errors.append(f"Invalid status: {story_data.get('status')}")
        
        # Metrics validation
        metrics = story_data.get("metrics", {})
        if metrics.get("word_count", 0) < 0:
            errors.append("Invalid word_count: cannot be negative")
        
        return len(errors) == 0, errors
    
    def validate_batch(self, data_type: str, batch: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Validate a batch of data"""
        valid_items = []
        invalid_items = []
        
        validators = {
            "user": self.validate_user,
            "session": self.validate_session,
            "story": self.validate_story
        }
        
        validator = validators.get(data_type)
        if not validator:
            logger.error(f"No validator for data type: {data_type}")
            return [], batch
        
        for item in batch:
            is_valid, errors = validator(item)
            if is_valid:
                valid_items.append(item)
            else:
                invalid_items.append({
                    "data": item,
                    "errors": errors
                })
                logger.warning(f"Invalid {data_type}: {errors}")
        
        return valid_items, invalid_items


class DataTransformer:
    """Transforms data between formats"""
    
    def transform_in_memory_session(self, session) -> Dict:
        """Transform in-memory session to persistable format"""
        try:
            # Handle both dict and object formats
            if hasattr(session, 'to_dict'):
                return session.to_dict()
            elif isinstance(session, dict):
                return session
            else:
                # Manual transformation
                return {
                    "session_id": getattr(session, 'session_id', None),
                    "user_id": getattr(session, 'user_id', None),
                    "status": getattr(session, 'status', 'active'),
                    "current_stage": getattr(session, 'current_stage', 'kickoff'),
                    "created_at": getattr(session, 'created_at', datetime.utcnow()).isoformat(),
                    "updated_at": getattr(session, 'updated_at', datetime.utcnow()).isoformat(),
                    "conversation_history": self._transform_conversation_history(session),
                    "story_elements": self._transform_story_elements(session),
                    "metadata": getattr(session, 'metadata', {})
                }
        except Exception as e:
            logger.error(f"Failed to transform session: {e}")
            raise
    
    def _transform_conversation_history(self, session) -> List[Dict]:
        """Transform conversation history"""
        history = getattr(session, 'conversation_history', [])
        transformed = []
        
        for turn in history:
            if hasattr(turn, 'to_dict'):
                transformed.append(turn.to_dict())
            elif isinstance(turn, dict):
                transformed.append(turn)
            else:
                # Manual transformation
                transformed.append({
                    "turn": getattr(turn, 'turn', 0),
                    "stage": getattr(turn, 'stage', ''),
                    "user_input": getattr(turn, 'user_input', None),
                    "llm_response": getattr(turn, 'llm_response', None),
                    "timestamp": getattr(turn, 'timestamp', datetime.utcnow().isoformat()),
                    "context_used": getattr(turn, 'context_used', [])
                })
        
        return transformed
    
    def _transform_story_elements(self, session) -> Dict:
        """Transform story elements"""
        elements = getattr(session, 'story_elements', None)
        if not elements:
            return {}
        
        if hasattr(elements, 'to_dict'):
            return elements.to_dict()
        elif isinstance(elements, dict):
            return elements
        else:
            # Manual transformation
            return {
                "core_idea": getattr(elements, 'core_idea', None),
                "personal_anecdote": getattr(elements, 'personal_anecdote', None),
                "selected_hook": getattr(elements, 'selected_hook', None),
                "richmond_quote": getattr(elements, 'richmond_quote', None),
                "selected_cta": getattr(elements, 'selected_cta', None),
                "final_story": getattr(elements, 'final_story', None)
            }
    
    def transform_json_export(self, json_data: Dict, data_type: str) -> Dict:
        """Transform JSON export data to model format"""
        # Add any necessary transformations
        # For now, most JSON exports should be compatible
        return json_data
    
    def generate_missing_ids(self, data: Dict, data_type: str) -> Dict:
        """Generate IDs for data missing them"""
        id_field = f"{data_type}_id"
        
        if not data.get(id_field):
            # Generate deterministic ID based on content
            content = json.dumps(data, sort_keys=True)
            hash_id = hashlib.md5(content.encode()).hexdigest()
            data[id_field] = f"{data_type}_{hash_id[:16]}"
        
        return data


class MigrationEngine:
    """Main migration engine"""
    
    def __init__(self, config: MigrationConfig = MigrationConfig()):
        self.config = config
        self.validator = MigrationValidator()
        self.transformer = DataTransformer()
        
        # Initialize repositories
        self.repositories = {
            'user': UserRepository(),
            'session': SessionRepository(),
            'story': StoryRepository(),
            'template': TemplateRepository(),
            'content': RichmondContentRepository()
        }
        
        # Initialize DynamoDB manager
        self.db_manager = DynamoDBManager(region=config.target_region)
        
        # Migration state
        self.state = {
            "status": "not_started",
            "start_time": None,
            "end_time": None,
            "items_processed": 0,
            "items_migrated": 0,
            "items_failed": 0,
            "errors": [],
            "checkpoint": None,
            "backup_id": None
        }
        
        # Load checkpoint if exists
        self._load_checkpoint()
    
    async def migrate_all(self) -> Dict[str, Any]:
        """Run complete migration"""
        self.state["status"] = "running"
        self.state["start_time"] = datetime.utcnow()
        
        logger.info(f"Starting migration (dry_run={self.config.dry_run})")
        
        try:
            # Create backup if enabled
            if self.config.create_backup and not self.config.dry_run:
                await self._create_pre_migration_backup()
            
            # Create tables if needed
            if self.config.create_tables and not self.config.dry_run:
                await self._create_tables()
            
            # Migrate each data type
            results = {
                "sessions": await self._migrate_sessions(),
                "users": await self._migrate_users(),
                "stories": await self._migrate_stories(),
                "templates": await self._migrate_templates(),
                "content": await self._migrate_content()
            }
            
            # Verify migration
            if self.config.validate_data:
                results["verification"] = await self._verify_migration()
            
            # Update state
            self.state["status"] = "completed"
            self.state["end_time"] = datetime.utcnow()
            self.state["results"] = results
            
            logger.info(f"Migration completed: {self.state['items_migrated']} items migrated")
            
            return self.state
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.state["status"] = "failed"
            self.state["errors"].append(str(e))
            
            # Rollback if enabled
            if self.config.enable_rollback and self.config.rollback_on_error:
                await self._rollback()
            
            raise
        finally:
            # Save final state
            self._save_checkpoint()
    
    async def _create_pre_migration_backup(self):
        """Create backup before migration"""
        logger.info("Creating pre-migration backup...")
        
        backup_manager = BackupManager()
        backup_result = await backup_manager.backup_all("pre_migration")
        
        if backup_result["success"]:
            self.state["backup_id"] = backup_result["backup_id"]
            logger.info(f"Backup created: {self.state['backup_id']}")
        else:
            raise Exception("Failed to create pre-migration backup")
    
    async def _create_tables(self):
        """Create DynamoDB tables"""
        logger.info("Creating DynamoDB tables...")
        
        results = self.db_manager.create_all_tables()
        
        # Wait for tables to be active
        for table_name, created in results.items():
            if created:
                while self.db_manager.get_table_status(table_name) != "ACTIVE":
                    await asyncio.sleep(2)
                logger.info(f"Table {table_name} is active")
    
    async def _migrate_sessions(self) -> Dict[str, Any]:
        """Migrate session data"""
        logger.info("Migrating sessions...")
        
        migrated = 0
        failed = 0
        
        if self.config.source_type == "in_memory":
            # Get all sessions from in-memory store
            sessions = []
            for session_id, session in in_memory_session_store._sessions.items():
                sessions.append(session)
        else:
            # Load from file or other source
            sessions = await self._load_data("sessions")
        
        # Process in batches
        for i in range(0, len(sessions), self.config.batch_size):
            batch = sessions[i:i + self.config.batch_size]
            
            # Transform and validate
            transformed_batch = []
            for session in batch:
                try:
                    session_data = self.transformer.transform_in_memory_session(session)
                    transformed_batch.append(session_data)
                except Exception as e:
                    logger.error(f"Failed to transform session: {e}")
                    failed += 1
            
            # Validate batch
            valid_sessions, invalid_sessions = self.validator.validate_batch("session", transformed_batch)
            failed += len(invalid_sessions)
            
            # Migrate valid sessions
            if not self.config.dry_run:
                for session_data in valid_sessions:
                    try:
                        session_obj = Session.from_dict(session_data)
                        if self.repositories['session'].save(session_obj):
                            migrated += 1
                            # Cache active sessions
                            if session_obj.status.value == "active":
                                entity_cache.set_session(session_obj)
                    except Exception as e:
                        logger.error(f"Failed to save session: {e}")
                        failed += 1
            else:
                migrated += len(valid_sessions)
            
            # Update state
            self.state["items_processed"] += len(batch)
            self.state["items_migrated"] += migrated
            self.state["items_failed"] += failed
            
            # Save checkpoint
            if self.state["items_processed"] % self.config.checkpoint_interval == 0:
                self._save_checkpoint()
        
        return {
            "total": len(sessions),
            "migrated": migrated,
            "failed": failed
        }
    
    async def _migrate_users(self) -> Dict[str, Any]:
        """Migrate user data"""
        logger.info("Migrating users...")
        
        # Similar pattern to sessions
        # Load users from source
        users = await self._load_data("users")
        
        migrated = 0
        failed = 0
        
        for i in range(0, len(users), self.config.batch_size):
            batch = users[i:i + self.config.batch_size]
            
            # Validate batch
            valid_users, invalid_users = self.validator.validate_batch("user", batch)
            failed += len(invalid_users)
            
            # Migrate valid users
            if not self.config.dry_run:
                for user_data in valid_users:
                    try:
                        user_obj = User.from_dict(user_data)
                        if self.repositories['user'].save(user_obj):
                            migrated += 1
                    except Exception as e:
                        logger.error(f"Failed to save user: {e}")
                        failed += 1
            else:
                migrated += len(valid_users)
        
        return {
            "total": len(users),
            "migrated": migrated,
            "failed": failed
        }
    
    async def _migrate_stories(self) -> Dict[str, Any]:
        """Migrate story data"""
        logger.info("Migrating stories...")
        
        stories = await self._load_data("stories")
        
        migrated = 0
        failed = 0
        
        for i in range(0, len(stories), self.config.batch_size):
            batch = stories[i:i + self.config.batch_size]
            
            # Validate batch
            valid_stories, invalid_stories = self.validator.validate_batch("story", batch)
            failed += len(invalid_stories)
            
            # Migrate valid stories
            if not self.config.dry_run:
                for story_data in valid_stories:
                    try:
                        story_obj = Story.from_dict(story_data)
                        if self.repositories['story'].save(story_obj):
                            migrated += 1
                            # Cache recent stories
                            if story_obj.status.value == "published":
                                entity_cache.set_story(story_obj)
                    except Exception as e:
                        logger.error(f"Failed to save story: {e}")
                        failed += 1
            else:
                migrated += len(valid_stories)
        
        return {
            "total": len(stories),
            "migrated": migrated,
            "failed": failed
        }
    
    async def _migrate_templates(self) -> Dict[str, Any]:
        """Migrate template data"""
        logger.info("Migrating templates...")
        
        templates = await self._load_data("templates")
        
        migrated = 0
        failed = 0
        
        for template_data in templates:
            try:
                if not self.config.dry_run:
                    template_obj = Template.from_dict(template_data)
                    if self.repositories['template'].save(template_obj):
                        migrated += 1
                        # Cache all templates
                        entity_cache.set_template(template_obj)
                else:
                    migrated += 1
            except Exception as e:
                logger.error(f"Failed to save template: {e}")
                failed += 1
        
        return {
            "total": len(templates),
            "migrated": migrated,
            "failed": failed
        }
    
    async def _migrate_content(self) -> Dict[str, Any]:
        """Migrate Richmond content data"""
        logger.info("Migrating Richmond content...")
        
        contents = await self._load_data("content")
        
        migrated = 0
        failed = 0
        
        # Batch process content
        content_batch = []
        for content_data in contents:
            try:
                content_obj = RichmondContent.from_dict(content_data)
                content_batch.append(content_obj)
                
                if len(content_batch) >= self.config.batch_size:
                    if not self.config.dry_run:
                        saved = self.repositories['content'].save_batch(content_batch)
                        migrated += saved
                    else:
                        migrated += len(content_batch)
                    content_batch = []
                    
            except Exception as e:
                logger.error(f"Failed to process content: {e}")
                failed += 1
        
        # Save remaining batch
        if content_batch and not self.config.dry_run:
            saved = self.repositories['content'].save_batch(content_batch)
            migrated += saved
        elif content_batch:
            migrated += len(content_batch)
        
        return {
            "total": len(contents),
            "migrated": migrated,
            "failed": failed
        }
    
    async def _load_data(self, data_type: str) -> List[Dict]:
        """Load data from source"""
        if self.config.source_type == "json_files" and self.config.source_path:
            file_path = Path(self.config.source_path) / f"{data_type}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        
        # Return empty list if no data found
        return []
    
    async def _verify_migration(self) -> Dict[str, Any]:
        """Verify migration success"""
        logger.info("Verifying migration...")
        
        verification_results = {}
        
        # Verify counts
        for entity_type, repo in self.repositories.items():
            try:
                # Get count from source
                source_count = len(await self._load_data(entity_type))
                
                # Get count from target (simplified - would need proper counting)
                target_count = self.state["items_migrated"]  # Simplified
                
                verification_results[entity_type] = {
                    "source_count": source_count,
                    "target_count": target_count,
                    "match": source_count == target_count
                }
            except Exception as e:
                verification_results[entity_type] = {
                    "error": str(e)
                }
        
        return verification_results
    
    async def _rollback(self):
        """Rollback migration"""
        logger.warning("Rolling back migration...")
        
        if self.state["backup_id"]:
            # Restore from backup
            from .backup import RestoreManager
            restore_manager = RestoreManager()
            
            restore_result = await restore_manager.restore_backup(
                self.state["backup_id"],
                {"create_tables": False}
            )
            
            if restore_result["success"]:
                logger.info("Rollback completed")
            else:
                logger.error("Rollback failed")
    
    def _save_checkpoint(self):
        """Save migration checkpoint"""
        checkpoint_data = {
            "state": self.state,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with open(self.config.checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    
    def _load_checkpoint(self):
        """Load migration checkpoint"""
        if os.path.exists(self.config.checkpoint_file):
            try:
                with open(self.config.checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                    self.state = checkpoint_data["state"]
                    logger.info(f"Loaded checkpoint from {checkpoint_data['timestamp']}")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")


class MigrationMonitor:
    """Monitor migration progress"""
    
    def __init__(self, migration_engine: MigrationEngine):
        self.engine = migration_engine
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current migration progress"""
        state = self.engine.state
        
        progress = {
            "status": state["status"],
            "items_processed": state["items_processed"],
            "items_migrated": state["items_migrated"],
            "items_failed": state["items_failed"],
            "error_count": len(state["errors"]),
            "progress_percentage": 0
        }
        
        # Calculate progress
        if state["items_processed"] > 0:
            progress["progress_percentage"] = round(
                (state["items_migrated"] / state["items_processed"]) * 100, 2
            )
        
        # Calculate ETA
        if state["start_time"] and state["items_processed"] > 0:
            elapsed = (datetime.utcnow() - state["start_time"]).total_seconds()
            rate = state["items_processed"] / elapsed
            
            progress["processing_rate"] = round(rate, 2)
            progress["elapsed_time"] = elapsed
        
        return progress
    
    async def monitor_migration(self, update_interval: int = 5):
        """Monitor migration with periodic updates"""
        while self.engine.state["status"] == "running":
            progress = self.get_progress()
            logger.info(f"Migration progress: {progress['progress_percentage']}% "
                       f"({progress['items_migrated']} migrated, "
                       f"{progress['items_failed']} failed)")
            
            await asyncio.sleep(update_interval)


# Convenience functions
async def run_migration(config: Optional[MigrationConfig] = None) -> Dict[str, Any]:
    """Run data migration"""
    config = config or MigrationConfig()
    engine = MigrationEngine(config)
    
    # Start monitoring in background
    monitor = MigrationMonitor(engine)
    monitor_task = asyncio.create_task(monitor.monitor_migration())
    
    try:
        result = await engine.migrate_all()
        return result
    finally:
        monitor_task.cancel()


async def verify_migration() -> Dict[str, Any]:
    """Verify migration success"""
    engine = MigrationEngine()
    return await engine._verify_migration()


def export_in_memory_data(output_dir: str = "migration_export"):
    """Export in-memory data to JSON files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Export sessions
    sessions = []
    transformer = DataTransformer()
    
    for session_id, session in in_memory_session_store._sessions.items():
        try:
            session_data = transformer.transform_in_memory_session(session)
            sessions.append(session_data)
        except Exception as e:
            logger.error(f"Failed to export session {session_id}: {e}")
    
    with open(output_path / "sessions.json", 'w') as f:
        json.dump(sessions, f, indent=2)
    
    logger.info(f"Exported {len(sessions)} sessions to {output_path}")
    
    return {
        "output_directory": str(output_path),
        "sessions_exported": len(sessions)
    }