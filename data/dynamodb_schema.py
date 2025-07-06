"""
DynamoDB schema definitions and table configurations
Implements single-table design with GSIs for efficient queries
"""
import boto3
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger('storygen.dynamodb')


class DynamoDBTables:
    """DynamoDB table definitions and configurations"""
    
    # Table names
    MAIN_TABLE = "storygen-main"
    ANALYTICS_TABLE = "storygen-analytics"
    CACHE_TABLE = "storygen-cache"
    
    # Entity types (for single-table design)
    ENTITY_USER = "USER"
    ENTITY_SESSION = "SESSION"
    ENTITY_STORY = "STORY"
    ENTITY_TEMPLATE = "TEMPLATE"
    ENTITY_CONTENT = "CONTENT"
    
    # Index names
    GSI_USER_CREATED = "gsi-user-created"
    GSI_TYPE_STATUS = "gsi-type-status"
    GSI_USER_SESSION = "gsi-user-session"
    GSI_CONTENT_TYPE = "gsi-content-type"
    GSI_TIMESTAMP = "gsi-timestamp"
    
    @classmethod
    def get_table_definitions(cls) -> Dict[str, Any]:
        """Get complete table definitions for creation"""
        return {
            cls.MAIN_TABLE: cls._main_table_definition(),
            cls.ANALYTICS_TABLE: cls._analytics_table_definition(),
            cls.CACHE_TABLE: cls._cache_table_definition()
        }
    
    @classmethod
    def _main_table_definition(cls) -> Dict[str, Any]:
        """Main table schema using single-table design"""
        return {
            "TableName": cls.MAIN_TABLE,
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "sk", "KeyType": "RANGE"}   # Sort key
            ],
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "gsi1pk", "AttributeType": "S"},
                {"AttributeName": "gsi1sk", "AttributeType": "S"},
                {"AttributeName": "gsi2pk", "AttributeType": "S"},
                {"AttributeName": "gsi2sk", "AttributeType": "S"},
                {"AttributeName": "gsi3pk", "AttributeType": "S"},
                {"AttributeName": "gsi3sk", "AttributeType": "S"},
                {"AttributeName": "gsi4pk", "AttributeType": "S"},
                {"AttributeName": "gsi4sk", "AttributeType": "S"},
                {"AttributeName": "ttl", "AttributeType": "N"}
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": cls.GSI_USER_CREATED,
                    "Keys": [
                        {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi1sk", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                },
                {
                    "IndexName": cls.GSI_TYPE_STATUS,
                    "Keys": [
                        {"AttributeName": "gsi2pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi2sk", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                },
                {
                    "IndexName": cls.GSI_USER_SESSION,
                    "Keys": [
                        {"AttributeName": "gsi3pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi3sk", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                },
                {
                    "IndexName": cls.GSI_CONTENT_TYPE,
                    "Keys": [
                        {"AttributeName": "gsi4pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi4sk", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            },
            "StreamSpecification": {
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            },
            "TimeToLiveSpecification": {
                "AttributeName": "ttl",
                "Enabled": True
            },
            "Tags": [
                {"Key": "Application", "Value": "StoryGen"},
                {"Key": "Environment", "Value": "production"}
            ]
        }
    
    @classmethod
    def _analytics_table_definition(cls) -> Dict[str, Any]:
        """Analytics table for time-series data"""
        return {
            "TableName": cls.ANALYTICS_TABLE,
            "KeySchema": [
                {"AttributeName": "pk", "KeyType": "HASH"},  # user_id or session_id
                {"AttributeName": "sk", "KeyType": "RANGE"}   # timestamp#event_id
            ],
            "AttributeDefinitions": [
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "event_type", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"}
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": cls.GSI_TIMESTAMP,
                    "Keys": [
                        {"AttributeName": "event_type", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 10
                    }
                }
            ],
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 20
            },
            "StreamSpecification": {
                "StreamEnabled": True,
                "StreamViewType": "NEW_IMAGE"
            },
            "Tags": [
                {"Key": "Application", "Value": "StoryGen"},
                {"Key": "DataType", "Value": "Analytics"}
            ]
        }
    
    @classmethod
    def _cache_table_definition(cls) -> Dict[str, Any]:
        """Cache table with TTL for temporary data"""
        return {
            "TableName": cls.CACHE_TABLE,
            "KeySchema": [
                {"AttributeName": "cache_key", "KeyType": "HASH"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "cache_key", "AttributeType": "S"}
            ],
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            },
            "TimeToLiveSpecification": {
                "AttributeName": "ttl",
                "Enabled": True
            },
            "Tags": [
                {"Key": "Application", "Value": "StoryGen"},
                {"Key": "DataType", "Value": "Cache"}
            ]
        }


class DynamoDBKeyBuilder:
    """Helper class to build consistent keys for single-table design"""
    
    @staticmethod
    def user_key(user_id: str) -> Dict[str, str]:
        """Build primary key for user"""
        return {
            "pk": f"USER#{user_id}",
            "sk": "PROFILE"
        }
    
    @staticmethod
    def session_key(session_id: str) -> Dict[str, str]:
        """Build primary key for session"""
        return {
            "pk": f"SESSION#{session_id}",
            "sk": "METADATA"
        }
    
    @staticmethod
    def session_turn_key(session_id: str, turn_number: int) -> Dict[str, str]:
        """Build key for session conversation turn"""
        return {
            "pk": f"SESSION#{session_id}",
            "sk": f"TURN#{turn_number:04d}"
        }
    
    @staticmethod
    def story_key(story_id: str) -> Dict[str, str]:
        """Build primary key for story"""
        return {
            "pk": f"STORY#{story_id}",
            "sk": "CONTENT"
        }
    
    @staticmethod
    def story_version_key(story_id: str, version: int) -> Dict[str, str]:
        """Build key for story version"""
        return {
            "pk": f"STORY#{story_id}",
            "sk": f"VERSION#{version:04d}"
        }
    
    @staticmethod
    def template_key(template_id: str) -> Dict[str, str]:
        """Build primary key for template"""
        return {
            "pk": f"TEMPLATE#{template_id}",
            "sk": "DEFINITION"
        }
    
    @staticmethod
    def content_key(content_id: str) -> Dict[str, str]:
        """Build primary key for Richmond content"""
        return {
            "pk": f"CONTENT#{content_id}",
            "sk": "CHUNK"
        }
    
    @staticmethod
    def user_stories_gsi(user_id: str, created_at: datetime) -> Dict[str, str]:
        """Build GSI key for user's stories sorted by date"""
        return {
            "gsi1pk": f"USER#{user_id}",
            "gsi1sk": f"STORY#{created_at.isoformat()}"
        }
    
    @staticmethod
    def type_status_gsi(entity_type: str, status: str, timestamp: datetime) -> Dict[str, str]:
        """Build GSI key for entity type and status queries"""
        return {
            "gsi2pk": f"{entity_type}#{status}",
            "gsi2sk": timestamp.isoformat()
        }
    
    @staticmethod
    def user_session_gsi(user_id: str, session_id: str) -> Dict[str, str]:
        """Build GSI key for user's sessions"""
        return {
            "gsi3pk": f"USER#{user_id}",
            "gsi3sk": f"SESSION#{session_id}"
        }
    
    @staticmethod
    def content_type_gsi(content_type: str, created_at: datetime) -> Dict[str, str]:
        """Build GSI key for content type queries"""
        return {
            "gsi4pk": f"CONTENT_TYPE#{content_type}",
            "gsi4sk": created_at.isoformat()
        }
    
    @staticmethod
    def analytics_key(entity_id: str, timestamp: datetime, event_id: str) -> Dict[str, str]:
        """Build key for analytics events"""
        return {
            "pk": entity_id,
            "sk": f"{timestamp.isoformat()}#{event_id}"
        }
    
    @staticmethod
    def cache_key(key_parts: List[str]) -> str:
        """Build cache key from parts"""
        return ":".join(key_parts)


class DynamoDBManager:
    """Manages DynamoDB table creation and configuration"""
    
    def __init__(self, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        """Initialize DynamoDB manager"""
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=region,
            endpoint_url=endpoint_url  # For local development with DynamoDB Local
        )
        self.client = boto3.client(
            'dynamodb',
            region_name=region,
            endpoint_url=endpoint_url
        )
    
    def create_all_tables(self) -> Dict[str, bool]:
        """Create all required tables"""
        results = {}
        for table_name, table_def in DynamoDBTables.get_table_definitions().items():
            results[table_name] = self.create_table(table_def)
        return results
    
    def create_table(self, table_definition: Dict[str, Any]) -> bool:
        """Create a single table"""
        table_name = table_definition["TableName"]
        try:
            # Check if table already exists
            existing_tables = self.client.list_tables()['TableNames']
            if table_name in existing_tables:
                logger.info(f"Table {table_name} already exists")
                return True
            
            # Create table
            table = self.dynamodb.create_table(**table_definition)
            
            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"Created table {table_name}")
            
            # Enable point-in-time recovery
            self.enable_pitr(table_name)
            
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def enable_pitr(self, table_name: str):
        """Enable point-in-time recovery for a table"""
        try:
            self.client.update_continuous_backups(
                TableName=table_name,
                PointInTimeRecoverySpecification={
                    'PointInTimeRecoveryEnabled': True
                }
            )
            logger.info(f"Enabled PITR for table {table_name}")
        except ClientError as e:
            logger.warning(f"Failed to enable PITR for {table_name}: {e}")
    
    def delete_all_tables(self) -> Dict[str, bool]:
        """Delete all tables (for testing/development)"""
        results = {}
        for table_name in DynamoDBTables.get_table_definitions().keys():
            results[table_name] = self.delete_table(table_name)
        return results
    
    def delete_table(self, table_name: str) -> bool:
        """Delete a single table"""
        try:
            table = self.dynamodb.Table(table_name)
            table.delete()
            logger.info(f"Deleted table {table_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete table {table_name}: {e}")
            return False
    
    def get_table_status(self, table_name: str) -> Optional[str]:
        """Get table status"""
        try:
            response = self.client.describe_table(TableName=table_name)
            return response['Table']['TableStatus']
        except ClientError:
            return None
    
    def update_table_capacity(self, table_name: str, read_units: int, write_units: int):
        """Update table capacity"""
        try:
            self.client.update_table(
                TableName=table_name,
                ProvisionedThroughput={
                    'ReadCapacityUnits': read_units,
                    'WriteCapacityUnits': write_units
                }
            )
            logger.info(f"Updated capacity for {table_name}: R={read_units}, W={write_units}")
        except ClientError as e:
            logger.error(f"Failed to update capacity for {table_name}: {e}")
    
    def enable_auto_scaling(self, table_name: str):
        """Enable auto-scaling for a table"""
        # This would use AWS Application Auto Scaling
        # Implementation depends on specific scaling policies
        pass