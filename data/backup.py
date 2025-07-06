"""
Backup and disaster recovery system for Richmond Storyline Generator
Implements automated backups to S3 with point-in-time recovery
"""
import boto3
import json
import gzip
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import schedule
import time
from dataclasses import dataclass
from botocore.exceptions import ClientError

from .models import User, Story, Session, Template, RichmondContent
from .dynamodb_schema import DynamoDBTables, DynamoDBManager
from .repositories import (
    UserRepository, SessionRepository, StoryRepository,
    TemplateRepository, RichmondContentRepository
)

logger = logging.getLogger('storygen.backup')


@dataclass
class BackupConfig:
    """Backup configuration settings"""
    # S3 settings
    s3_bucket: str = "storygen-backups"
    s3_prefix: str = "backups"
    s3_region: str = "us-east-1"
    
    # Backup settings
    retention_days: int = 30
    compression: bool = True
    encryption: bool = True
    
    # Schedule settings
    daily_backup_time: str = "02:00"  # 2 AM
    weekly_backup_day: str = "sunday"
    monthly_backup_day: int = 1
    
    # Performance settings
    batch_size: int = 1000
    max_workers: int = 4
    
    # Local backup directory
    local_backup_dir: str = "backups"
    keep_local_copy: bool = True


class BackupManager:
    """Manages backup operations"""
    
    def __init__(self, config: BackupConfig = BackupConfig()):
        self.config = config
        self.s3_client = boto3.client('s3', region_name=config.s3_region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=config.s3_region)
        
        # Initialize repositories
        self.repositories = {
            'user': UserRepository(),
            'session': SessionRepository(),
            'story': StoryRepository(),
            'template': TemplateRepository(),
            'content': RichmondContentRepository()
        }
        
        # Create local backup directory
        Path(config.local_backup_dir).mkdir(parents=True, exist_ok=True)
        
        # Backup statistics
        self.stats = {
            "last_backup": None,
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "total_size_bytes": 0
        }
    
    async def backup_all(self, backup_type: str = "daily") -> Dict[str, Any]:
        """Perform complete backup of all data"""
        backup_id = self._generate_backup_id(backup_type)
        start_time = datetime.utcnow()
        
        logger.info(f"Starting {backup_type} backup: {backup_id}")
        
        results = {
            "backup_id": backup_id,
            "backup_type": backup_type,
            "start_time": start_time.isoformat(),
            "tables": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Backup each table
            tasks = [
                self._backup_table(DynamoDBTables.MAIN_TABLE, backup_id),
                self._backup_table(DynamoDBTables.ANALYTICS_TABLE, backup_id),
                self._backup_table(DynamoDBTables.CACHE_TABLE, backup_id),
                self._backup_vector_index(backup_id),
                self._backup_metadata(backup_id)
            ]
            
            # Execute backups in parallel
            backup_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(backup_results):
                if isinstance(result, Exception):
                    results["success"] = False
                    results["errors"].append(str(result))
                    logger.error(f"Backup task {i} failed: {result}")
                else:
                    if i < 3:  # Table backups
                        table_name = [DynamoDBTables.MAIN_TABLE, 
                                    DynamoDBTables.ANALYTICS_TABLE,
                                    DynamoDBTables.CACHE_TABLE][i]
                        results["tables"][table_name] = result
                    elif i == 3:  # Vector index
                        results["vector_index"] = result
                    else:  # Metadata
                        results["metadata"] = result
            
            # Calculate total size
            total_size = sum(
                table_info.get("size_bytes", 0) 
                for table_info in results["tables"].values()
            )
            results["total_size_bytes"] = total_size
            results["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            # Update statistics
            self.stats["total_backups"] += 1
            if results["success"]:
                self.stats["successful_backups"] += 1
                self.stats["last_backup"] = start_time
                self.stats["total_size_bytes"] += total_size
            else:
                self.stats["failed_backups"] += 1
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            # Record backup completion
            end_time = datetime.utcnow()
            results["end_time"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            logger.info(f"Backup {backup_id} completed: {results['success']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            self.stats["failed_backups"] += 1
            return results
    
    async def _backup_table(self, table_name: str, backup_id: str) -> Dict[str, Any]:
        """Backup a single DynamoDB table"""
        logger.info(f"Backing up table: {table_name}")
        
        try:
            # Use DynamoDB point-in-time recovery if available
            pitr_backup = await self._create_pitr_backup(table_name, backup_id)
            if pitr_backup:
                return pitr_backup
            
            # Fall back to manual export
            items = []
            scan_kwargs = {
                'TableName': table_name,
                'Limit': self.config.batch_size
            }
            
            # Scan all items
            while True:
                response = self.dynamodb_client.scan(**scan_kwargs)
                items.extend(response.get('Items', []))
                
                # Check for more items
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            logger.info(f"Scanned {len(items)} items from {table_name}")
            
            # Prepare backup data
            backup_data = {
                "table_name": table_name,
                "backup_id": backup_id,
                "timestamp": datetime.utcnow().isoformat(),
                "item_count": len(items),
                "items": items
            }
            
            # Serialize and compress
            json_data = json.dumps(backup_data, default=str)
            
            if self.config.compression:
                data = gzip.compress(json_data.encode('utf-8'))
                file_extension = "json.gz"
            else:
                data = json_data.encode('utf-8')
                file_extension = "json"
            
            # Generate S3 key
            s3_key = f"{self.config.s3_prefix}/{backup_id}/tables/{table_name}.{file_extension}"
            
            # Upload to S3
            extra_args = {}
            if self.config.encryption:
                extra_args['ServerSideEncryption'] = 'AES256'
            
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=data,
                **extra_args
            )
            
            # Save local copy if configured
            if self.config.keep_local_copy:
                local_path = Path(self.config.local_backup_dir) / backup_id / "tables"
                local_path.mkdir(parents=True, exist_ok=True)
                local_file = local_path / f"{table_name}.{file_extension}"
                local_file.write_bytes(data)
            
            return {
                "table_name": table_name,
                "item_count": len(items),
                "size_bytes": len(data),
                "s3_key": s3_key,
                "compressed": self.config.compression,
                "encrypted": self.config.encryption
            }
            
        except Exception as e:
            logger.error(f"Failed to backup table {table_name}: {e}")
            raise
    
    async def _create_pitr_backup(self, table_name: str, backup_id: str) -> Optional[Dict[str, Any]]:
        """Create point-in-time recovery backup"""
        try:
            # Create on-demand backup
            response = self.dynamodb_client.create_backup(
                TableName=table_name,
                BackupName=f"{backup_id}-{table_name}"
            )
            
            backup_arn = response['BackupDetails']['BackupArn']
            
            return {
                "table_name": table_name,
                "backup_method": "pitr",
                "backup_arn": backup_arn,
                "status": response['BackupDetails']['BackupStatus']
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ContinuousBackupsUnavailableException':
                logger.info(f"PITR not enabled for {table_name}, using manual backup")
                return None
            raise
    
    async def _backup_vector_index(self, backup_id: str) -> Dict[str, Any]:
        """Backup Pinecone vector index metadata"""
        logger.info("Backing up vector index metadata")
        
        try:
            # Get all content with embeddings
            contents = []
            for content_type in ["quotes", "culture", "economy", "stories", "news"]:
                type_contents = self.repositories['content'].list_by_type(content_type, limit=10000)
                contents.extend([c for c in type_contents if c.embedding_id])
            
            # Create index mapping
            index_mapping = {
                c.embedding_id: {
                    "content_id": c.content_id,
                    "content_type": c.content_type,
                    "source_file": c.source_file,
                    "chunk_index": c.chunk_index
                }
                for c in contents
            }
            
            # Save mapping
            backup_data = {
                "backup_id": backup_id,
                "timestamp": datetime.utcnow().isoformat(),
                "vector_count": len(index_mapping),
                "mapping": index_mapping
            }
            
            json_data = json.dumps(backup_data)
            if self.config.compression:
                data = gzip.compress(json_data.encode('utf-8'))
                file_extension = "json.gz"
            else:
                data = json_data.encode('utf-8')
                file_extension = "json"
            
            # Upload to S3
            s3_key = f"{self.config.s3_prefix}/{backup_id}/vector_index.{file_extension}"
            
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=data,
                ServerSideEncryption='AES256' if self.config.encryption else None
            )
            
            return {
                "vector_count": len(index_mapping),
                "size_bytes": len(data),
                "s3_key": s3_key
            }
            
        except Exception as e:
            logger.error(f"Failed to backup vector index: {e}")
            raise
    
    async def _backup_metadata(self, backup_id: str) -> Dict[str, Any]:
        """Backup system metadata and configuration"""
        logger.info("Backing up system metadata")
        
        try:
            metadata = {
                "backup_id": backup_id,
                "timestamp": datetime.utcnow().isoformat(),
                "system_info": {
                    "version": "1.0.0",
                    "tables": {
                        "main": DynamoDBTables.MAIN_TABLE,
                        "analytics": DynamoDBTables.ANALYTICS_TABLE,
                        "cache": DynamoDBTables.CACHE_TABLE
                    },
                    "indexes": list(DynamoDBTables.__dict__.items())
                },
                "statistics": self.stats,
                "configuration": {
                    "backup_config": self.config.__dict__,
                    "retention_days": self.config.retention_days
                }
            }
            
            # Save metadata
            json_data = json.dumps(metadata, default=str, indent=2)
            
            # Upload to S3
            s3_key = f"{self.config.s3_prefix}/{backup_id}/metadata.json"
            
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=json_data,
                ServerSideEncryption='AES256' if self.config.encryption else None
            )
            
            # Always save metadata locally
            local_path = Path(self.config.local_backup_dir) / backup_id
            local_path.mkdir(parents=True, exist_ok=True)
            (local_path / "metadata.json").write_text(json_data)
            
            return {
                "size_bytes": len(json_data),
                "s3_key": s3_key
            }
            
        except Exception as e:
            logger.error(f"Failed to backup metadata: {e}")
            raise
    
    def _generate_backup_id(self, backup_type: str) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{backup_type}_{timestamp}"
    
    async def _cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)
            
            # List all backups
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=self.config.s3_prefix
            )
            
            objects_to_delete = []
            
            for page in pages:
                for obj in page.get('Contents', []):
                    # Check if object is older than retention period
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        objects_to_delete.append({'Key': obj['Key']})
            
            # Delete old backups in batches
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i+1000]
                    self.s3_client.delete_objects(
                        Bucket=self.config.s3_bucket,
                        Delete={'Objects': batch}
                    )
                
                logger.info(f"Deleted {len(objects_to_delete)} old backups")
            
            # Clean up local backups
            if self.config.keep_local_copy:
                local_backup_dir = Path(self.config.local_backup_dir)
                for backup_dir in local_backup_dir.iterdir():
                    if backup_dir.is_dir():
                        # Parse timestamp from directory name
                        try:
                            dir_parts = backup_dir.name.split('_')
                            if len(dir_parts) >= 3:
                                date_str = f"{dir_parts[1]}_{dir_parts[2]}"
                                backup_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                                if backup_date < cutoff_date:
                                    import shutil
                                    shutil.rmtree(backup_dir)
                                    logger.info(f"Deleted local backup: {backup_dir.name}")
                        except Exception as e:
                            logger.warning(f"Failed to parse backup directory {backup_dir.name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def list_backups(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            backups = []
            
            # List from S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket,
                Prefix=f"{self.config.s3_prefix}/",
                Delimiter='/'
            )
            
            for prefix in response.get('CommonPrefixes', []):
                backup_id = prefix['Prefix'].split('/')[-2]
                
                # Get metadata
                try:
                    metadata_key = f"{self.config.s3_prefix}/{backup_id}/metadata.json"
                    metadata_obj = self.s3_client.get_object(
                        Bucket=self.config.s3_bucket,
                        Key=metadata_key
                    )
                    metadata = json.loads(metadata_obj['Body'].read())
                    
                    backups.append({
                        "backup_id": backup_id,
                        "timestamp": metadata.get("timestamp"),
                        "type": backup_id.split('_')[0],
                        "size_bytes": metadata_obj.get('ContentLength', 0)
                    })
                except Exception:
                    # If metadata is missing, extract info from backup_id
                    backups.append({
                        "backup_id": backup_id,
                        "type": backup_id.split('_')[0]
                    })
            
            # Sort by timestamp (most recent first)
            backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return backups[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup"""
        try:
            # Get metadata
            metadata_key = f"{self.config.s3_prefix}/{backup_id}/metadata.json"
            metadata_obj = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=metadata_key
            )
            metadata = json.loads(metadata_obj['Body'].read())
            
            # List all objects in backup
            objects = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=f"{self.config.s3_prefix}/{backup_id}/"
            )
            
            total_size = 0
            for page in pages:
                for obj in page.get('Contents', []):
                    objects.append({
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat()
                    })
                    total_size += obj['Size']
            
            return {
                "backup_id": backup_id,
                "metadata": metadata,
                "objects": objects,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup info for {backup_id}: {e}")
            return None


class RestoreManager:
    """Manages restore operations"""
    
    def __init__(self, config: BackupConfig = BackupConfig()):
        self.config = config
        self.s3_client = boto3.client('s3', region_name=config.s3_region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=config.s3_region)
        self.dynamodb_manager = DynamoDBManager(region=config.s3_region)
    
    async def restore_backup(self, backup_id: str, restore_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Restore from backup"""
        start_time = datetime.utcnow()
        restore_options = restore_options or {}
        
        logger.info(f"Starting restore from backup: {backup_id}")
        
        results = {
            "backup_id": backup_id,
            "start_time": start_time.isoformat(),
            "restore_options": restore_options,
            "tables": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Get backup metadata
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            results["backup_metadata"] = metadata
            
            # Restore tables
            tables_to_restore = restore_options.get('tables', [
                DynamoDBTables.MAIN_TABLE,
                DynamoDBTables.ANALYTICS_TABLE,
                DynamoDBTables.CACHE_TABLE
            ])
            
            for table_name in tables_to_restore:
                try:
                    table_result = await self._restore_table(backup_id, table_name, restore_options)
                    results["tables"][table_name] = table_result
                except Exception as e:
                    logger.error(f"Failed to restore table {table_name}: {e}")
                    results["errors"].append(f"Table {table_name}: {str(e)}")
                    results["success"] = False
            
            # Restore vector index if requested
            if restore_options.get('restore_vectors', True):
                try:
                    vector_result = await self._restore_vector_index(backup_id)
                    results["vector_index"] = vector_result
                except Exception as e:
                    logger.error(f"Failed to restore vector index: {e}")
                    results["errors"].append(f"Vector index: {str(e)}")
            
            # Complete restore
            end_time = datetime.utcnow()
            results["end_time"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            
            logger.info(f"Restore completed: {results['success']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup metadata"""
        try:
            metadata_key = f"{self.config.s3_prefix}/{backup_id}/metadata.json"
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=metadata_key
            )
            return json.loads(response['Body'].read())
        except Exception as e:
            logger.error(f"Failed to get backup metadata: {e}")
            return None
    
    async def _restore_table(self, backup_id: str, table_name: str, 
                           restore_options: Dict[str, Any]) -> Dict[str, Any]:
        """Restore a single table"""
        logger.info(f"Restoring table: {table_name}")
        
        # Check for PITR backup
        if restore_options.get('use_pitr', False):
            pitr_result = await self._restore_from_pitr(backup_id, table_name)
            if pitr_result:
                return pitr_result
        
        # Download backup file
        file_extension = "json.gz" if self.config.compression else "json"
        s3_key = f"{self.config.s3_prefix}/{backup_id}/tables/{table_name}.{file_extension}"
        
        response = self.s3_client.get_object(
            Bucket=self.config.s3_bucket,
            Key=s3_key
        )
        
        # Decompress if needed
        data = response['Body'].read()
        if self.config.compression:
            data = gzip.decompress(data)
        
        # Parse backup data
        backup_data = json.loads(data)
        items = backup_data['items']
        
        logger.info(f"Restoring {len(items)} items to {table_name}")
        
        # Create table if it doesn't exist
        if restore_options.get('create_tables', True):
            table_defs = DynamoDBTables.get_table_definitions()
            if table_name in table_defs:
                self.dynamodb_manager.create_table(table_defs[table_name])
        
        # Restore items in batches
        restored = 0
        failed = 0
        
        with self.dynamodb_client.Table(table_name).batch_writer() as batch:
            for item in items:
                try:
                    batch.put_item(Item=item)
                    restored += 1
                except Exception as e:
                    logger.error(f"Failed to restore item: {e}")
                    failed += 1
        
        return {
            "table_name": table_name,
            "total_items": len(items),
            "restored": restored,
            "failed": failed,
            "success": failed == 0
        }
    
    async def _restore_from_pitr(self, backup_id: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Restore from point-in-time recovery backup"""
        try:
            # Find backup ARN
            backups = self.dynamodb_client.list_backups(
                TableName=table_name,
                BackupType='USER'
            )
            
            backup_arn = None
            for backup in backups.get('BackupSummaries', []):
                if backup['BackupName'] == f"{backup_id}-{table_name}":
                    backup_arn = backup['BackupArn']
                    break
            
            if not backup_arn:
                return None
            
            # Restore table
            restore_table_name = f"{table_name}-restored-{int(time.time())}"
            
            response = self.dynamodb_client.restore_table_from_backup(
                TargetTableName=restore_table_name,
                BackupArn=backup_arn
            )
            
            return {
                "table_name": table_name,
                "restore_method": "pitr",
                "restored_table_name": restore_table_name,
                "status": response['TableDescription']['TableStatus']
            }
            
        except Exception as e:
            logger.error(f"PITR restore failed: {e}")
            return None
    
    async def _restore_vector_index(self, backup_id: str) -> Dict[str, Any]:
        """Restore vector index mapping"""
        logger.info("Restoring vector index mapping")
        
        try:
            # Download mapping file
            file_extension = "json.gz" if self.config.compression else "json"
            s3_key = f"{self.config.s3_prefix}/{backup_id}/vector_index.{file_extension}"
            
            response = self.s3_client.get_object(
                Bucket=self.config.s3_bucket,
                Key=s3_key
            )
            
            # Decompress if needed
            data = response['Body'].read()
            if self.config.compression:
                data = gzip.decompress(data)
            
            # Parse mapping data
            mapping_data = json.loads(data)
            mapping = mapping_data['mapping']
            
            # Update content records with embedding IDs
            content_repo = RichmondContentRepository()
            updated = 0
            
            for embedding_id, content_info in mapping.items():
                content = content_repo.get(content_info['content_id'])
                if content and not content.embedding_id:
                    content.embedding_id = embedding_id
                    if content_repo.save(content):
                        updated += 1
            
            return {
                "total_mappings": len(mapping),
                "updated": updated,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to restore vector index: {e}")
            raise


class BackupScheduler:
    """Schedules automated backups"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.config = backup_manager.config
        self._running = False
    
    def start(self):
        """Start backup scheduler"""
        self._running = True
        
        # Schedule daily backups
        schedule.every().day.at(self.config.daily_backup_time).do(
            lambda: asyncio.run(self.backup_manager.backup_all("daily"))
        )
        
        # Schedule weekly backups
        getattr(schedule.every(), self.config.weekly_backup_day).at("03:00").do(
            lambda: asyncio.run(self.backup_manager.backup_all("weekly"))
        )
        
        # Schedule monthly backups
        schedule.every().month.do(
            lambda: asyncio.run(self.backup_manager.backup_all("monthly"))
        )
        
        logger.info("Backup scheduler started")
        
        # Run scheduler
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop backup scheduler"""
        self._running = False
        logger.info("Backup scheduler stopped")


# Convenience functions
async def create_backup(backup_type: str = "manual") -> Dict[str, Any]:
    """Create a backup"""
    manager = BackupManager()
    return await manager.backup_all(backup_type)


async def restore_from_backup(backup_id: str, **options) -> Dict[str, Any]:
    """Restore from a backup"""
    manager = RestoreManager()
    return await manager.restore_backup(backup_id, options)


def list_available_backups(limit: int = 50) -> List[Dict[str, Any]]:
    """List available backups"""
    manager = BackupManager()
    return manager.list_backups(limit)


def start_backup_scheduler():
    """Start automated backup scheduler"""
    manager = BackupManager()
    scheduler = BackupScheduler(manager)
    scheduler.start()