"""
DynamoDB Schema and Migration Scripts for StoryGen
Handles table creation, indexes, and data migration
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from botocore.exceptions import ClientError


class DynamoDBSchema:
    """Manages DynamoDB schema and migrations"""
    
    def __init__(self, region: str = "us-east-1", env: str = "dev"):
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.client = boto3.client("dynamodb", region_name=region)
        self.env = env
        self.table_prefix = f"storygen-{env}"
        
    def create_main_table(self) -> None:
        """Create the main StoryGen table with access patterns"""
        table_name = f"{self.table_prefix}"
        
        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        "AttributeName": "pk",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "sk",
                        "KeyType": "RANGE"
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "pk",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "sk",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "gsi1pk",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "gsi1sk",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "userId",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "createdAt",
                        "AttributeType": "S"
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "GSI1",
                        "KeySchema": [
                            {
                                "AttributeName": "gsi1pk",
                                "KeyType": "HASH"
                            },
                            {
                                "AttributeName": "gsi1sk",
                                "KeyType": "RANGE"
                            }
                        ],
                        "Projection": {
                            "ProjectionType": "ALL"
                        },
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5
                        }
                    },
                    {
                        "IndexName": "GSI2",
                        "KeySchema": [
                            {
                                "AttributeName": "userId",
                                "KeyType": "HASH"
                            },
                            {
                                "AttributeName": "createdAt",
                                "KeyType": "RANGE"
                            }
                        ],
                        "Projection": {
                            "ProjectionType": "ALL"
                        },
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5
                        }
                    }
                ],
                BillingMode="PAY_PER_REQUEST" if self.env != "prod" else "PROVISIONED",
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                } if self.env == "prod" else None,
                StreamSpecification={
                    "StreamEnabled": True,
                    "StreamViewType": "NEW_AND_OLD_IMAGES"
                },
                PointInTimeRecoverySpecification={
                    "PointInTimeRecoveryEnabled": True
                },
                SSESpecification={
                    "Enabled": True,
                    "SSEType": "AES256"
                },
                Tags=[
                    {
                        "Key": "Project",
                        "Value": "StoryGen"
                    },
                    {
                        "Key": "Environment",
                        "Value": self.env
                    }
                ]
            )
            
            print(f"Creating table {table_name}...")
            table.wait_until_exists()
            print(f"Table {table_name} created successfully!")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"Table {table_name} already exists")
            else:
                raise
                
    def create_session_table(self) -> None:
        """Create session table with TTL"""
        table_name = f"{self.table_prefix}-sessions"
        
        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        "AttributeName": "sessionId",
                        "KeyType": "HASH"
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "sessionId",
                        "AttributeType": "S"
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
                StreamSpecification={
                    "StreamEnabled": False
                },
                SSESpecification={
                    "Enabled": True,
                    "SSEType": "AES256"
                },
                Tags=[
                    {
                        "Key": "Project",
                        "Value": "StoryGen"
                    },
                    {
                        "Key": "Environment",
                        "Value": self.env
                    }
                ]
            )
            
            print(f"Creating table {table_name}...")
            table.wait_until_exists()
            
            # Enable TTL
            self.client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    "Enabled": True,
                    "AttributeName": "ttl"
                }
            )
            
            print(f"Table {table_name} created successfully with TTL!")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"Table {table_name} already exists")
            else:
                raise
                
    def create_analytics_table(self) -> None:
        """Create analytics table for metrics"""
        table_name = f"{self.table_prefix}-analytics"
        
        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        "AttributeName": "metricType",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "timestamp",
                        "KeyType": "RANGE"
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "metricType",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "timestamp",
                        "AttributeType": "S"
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
                StreamSpecification={
                    "StreamEnabled": False
                },
                SSESpecification={
                    "Enabled": True,
                    "SSEType": "AES256"
                },
                Tags=[
                    {
                        "Key": "Project",
                        "Value": "StoryGen"
                    },
                    {
                        "Key": "Environment",
                        "Value": self.env
                    }
                ]
            )
            
            print(f"Creating table {table_name}...")
            table.wait_until_exists()
            print(f"Table {table_name} created successfully!")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"Table {table_name} already exists")
            else:
                raise
                
    def seed_initial_data(self) -> None:
        """Seed initial data for development"""
        if self.env == "prod":
            print("Skipping data seeding in production")
            return
            
        table = self.dynamodb.Table(f"{self.table_prefix}")
        
        # Sample story templates
        templates = [
            {
                "pk": "TEMPLATE#richmond-tech-return",
                "sk": "META",
                "gsi1pk": "TEMPLATES",
                "gsi1sk": "TEMPLATE#richmond-tech-return",
                "templateId": "richmond-tech-return",
                "name": "Tech Professional Returns Home",
                "description": "Story about tech professionals returning to Richmond from coastal cities",
                "style": "long_post",
                "tags": ["technology", "homecoming", "career"],
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            },
            {
                "pk": "TEMPLATE#startup-success",
                "sk": "META",
                "gsi1pk": "TEMPLATES",
                "gsi1sk": "TEMPLATE#startup-success",
                "templateId": "startup-success",
                "name": "Richmond Startup Success",
                "description": "Success stories from Richmond's growing startup ecosystem",
                "style": "blog_post",
                "tags": ["startup", "entrepreneurship", "success"],
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }
        ]
        
        # Sample system configuration
        config_items = [
            {
                "pk": "CONFIG#rate-limits",
                "sk": "SETTINGS",
                "configType": "rate-limits",
                "settings": {
                    "story_generation": {
                        "requests_per_minute": 10,
                        "requests_per_hour": 100,
                        "requests_per_day": 1000
                    },
                    "api_general": {
                        "requests_per_minute": 60,
                        "requests_per_hour": 3600
                    }
                },
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            },
            {
                "pk": "CONFIG#features",
                "sk": "FLAGS",
                "configType": "feature-flags",
                "features": {
                    "voice_input": True,
                    "collaborative_stories": False,
                    "ai_suggestions": True,
                    "export_pdf": False
                },
                "createdAt": datetime.utcnow().isoformat(),
                "updatedAt": datetime.utcnow().isoformat()
            }
        ]
        
        # Batch write
        with table.batch_writer() as batch:
            for template in templates:
                batch.put_item(Item=template)
                print(f"Seeded template: {template['name']}")
                
            for config in config_items:
                batch.put_item(Item=config)
                print(f"Seeded config: {config['configType']}")
                
        print("Initial data seeding completed!")
        
    def create_all_tables(self) -> None:
        """Create all required tables"""
        print(f"Creating DynamoDB tables for environment: {self.env}")
        
        self.create_main_table()
        self.create_session_table()
        self.create_analytics_table()
        
        # Wait for all tables to be active
        time.sleep(5)
        
        # Seed initial data
        self.seed_initial_data()
        
        print("All tables created successfully!")
        
    def describe_tables(self) -> None:
        """Describe all StoryGen tables"""
        tables = [
            f"{self.table_prefix}",
            f"{self.table_prefix}-sessions",
            f"{self.table_prefix}-analytics"
        ]
        
        for table_name in tables:
            try:
                response = self.client.describe_table(TableName=table_name)
                table_info = response["Table"]
                
                print(f"\n=== Table: {table_name} ===")
                print(f"Status: {table_info['TableStatus']}")
                print(f"Item Count: {table_info.get('ItemCount', 0)}")
                print(f"Size: {table_info.get('TableSizeBytes', 0)} bytes")
                print(f"Billing Mode: {table_info.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')}")
                
                if "GlobalSecondaryIndexes" in table_info:
                    print(f"GSIs: {len(table_info['GlobalSecondaryIndexes'])}")
                    for gsi in table_info["GlobalSecondaryIndexes"]:
                        print(f"  - {gsi['IndexName']}: {gsi['IndexStatus']}")
                        
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    print(f"\n=== Table: {table_name} ===")
                    print("Status: NOT FOUND")
                else:
                    raise
                    
    def delete_all_tables(self) -> None:
        """Delete all tables (use with caution!)"""
        if self.env == "prod":
            print("Cannot delete production tables!")
            return
            
        tables = [
            f"{self.table_prefix}",
            f"{self.table_prefix}-sessions",
            f"{self.table_prefix}-analytics"
        ]
        
        for table_name in tables:
            try:
                table = self.dynamodb.Table(table_name)
                table.delete()
                print(f"Deleting table {table_name}...")
                table.wait_until_not_exists()
                print(f"Table {table_name} deleted successfully!")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    print(f"Table {table_name} does not exist")
                else:
                    raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DynamoDB Schema Management for StoryGen")
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"], help="Environment")
    parser.add_argument("--region", default="us-east-1", help="AWS Region")
    parser.add_argument("--action", required=True, choices=["create", "describe", "delete", "seed"], help="Action to perform")
    
    args = parser.parse_args()
    
    schema = DynamoDBSchema(region=args.region, env=args.env)
    
    if args.action == "create":
        schema.create_all_tables()
    elif args.action == "describe":
        schema.describe_tables()
    elif args.action == "delete":
        if input(f"Are you sure you want to delete all {args.env} tables? (yes/no): ").lower() == "yes":
            schema.delete_all_tables()
        else:
            print("Deletion cancelled")
    elif args.action == "seed":
        schema.seed_initial_data()