"""
Data persistence and management layer for Richmond Storyline Generator
Provides comprehensive data storage, caching, analytics, and backup capabilities
"""
from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

# Import models
from .models import (
    User, Story, Session, Template, RichmondContent, Analytics,
    UserRole, StoryStyle, StoryStatus, TemplateCategory,
    generate_id, calculate_reading_time, extract_themes
)

# Import repositories
from .repositories import (
    UserRepository, SessionRepository, StoryRepository,
    TemplateRepository, RichmondContentRepository, AnalyticsRepository
)

# Import DynamoDB schema
from .dynamodb_schema import (
    DynamoDBTables, DynamoDBKeyBuilder, DynamoDBManager
)

# Import cache
from .cache import (
    CacheManager, EntityCache, CacheDecorator, CacheWarmer,
    cache_manager, entity_cache, cache_decorator
)

# Import pipeline
from .pipeline import (
    DataPipeline, PipelineConfig, run_ingestion_pipeline
)

# Import backup
from .backup import (
    BackupManager, RestoreManager, BackupScheduler,
    create_backup, restore_from_backup, list_available_backups
)

# Import analytics
from .analytics_engine import (
    AnalyticsCollector, AnalyticsProcessor, ReportGenerator,
    analytics_collector, analytics_processor, report_generator,
    track_event, track_api_call, get_analytics_dashboard, generate_report
)

# Import migration
from .migration import (
    MigrationEngine, MigrationConfig, run_migration,
    verify_migration, export_in_memory_data
)

logger = logging.getLogger('storygen.data')

# Global repository instances
repositories = {
    'user': UserRepository(),
    'session': SessionRepository(),
    'story': StoryRepository(),
    'template': TemplateRepository(),
    'content': RichmondContentRepository(),
    'analytics': AnalyticsRepository()
}


class DataManager:
    """Central data management interface"""
    
    def __init__(self):
        self.repositories = repositories
        self.cache = entity_cache
        self.analytics = analytics_collector
        self.initialized = False
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data layer"""
        logger.info("Initializing data management layer...")
        
        try:
            # Create DynamoDB tables if needed
            if config and config.get('create_tables', False):
                db_manager = DynamoDBManager()
                results = db_manager.create_all_tables()
                logger.info(f"Table creation results: {results}")
            
            # Warm cache if configured
            if config and config.get('warm_cache', True):
                warmer = CacheWarmer(cache_manager, self.repositories)
                await warmer.warm_cache()
            
            # Start analytics collector
            await self.analytics.start_collector()
            
            # Start backup scheduler if configured
            if config and config.get('enable_backups', False):
                backup_manager = BackupManager()
                scheduler = BackupScheduler(backup_manager)
                asyncio.create_task(self._run_backup_scheduler(scheduler))
            
            self.initialized = True
            logger.info("Data management layer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize data layer: {e}")
            raise
    
    async def _run_backup_scheduler(self, scheduler: BackupScheduler):
        """Run backup scheduler in background"""
        try:
            scheduler.start()
        except Exception as e:
            logger.error(f"Backup scheduler error: {e}")
    
    async def shutdown(self):
        """Shutdown data layer gracefully"""
        logger.info("Shutting down data management layer...")
        
        # Stop analytics collector
        await self.analytics.stop_collector()
        
        # Clear L1 cache
        cache_manager.clear_l1_cache()
        
        logger.info("Data management layer shutdown complete")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of data layer"""
        status = {
            "initialized": self.initialized,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check DynamoDB
        try:
            # Simple health check - try to query
            self.repositories['user'].list_by_role(UserRole.ADMIN, limit=1)
            status["components"]["dynamodb"] = "healthy"
        except Exception as e:
            status["components"]["dynamodb"] = f"unhealthy: {str(e)}"
        
        # Check Redis cache
        try:
            cache_manager.redis.ping()
            status["components"]["redis"] = "healthy"
            status["cache_stats"] = cache_manager.get_stats()
        except Exception as e:
            status["components"]["redis"] = f"unhealthy: {str(e)}"
        
        # Check repositories
        for name, repo in self.repositories.items():
            status["components"][f"repository_{name}"] = "healthy"
        
        return status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data layer statistics"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": cache_manager.get_stats(),
            "repositories": {},
            "analytics": {
                "events_queued": analytics_collector.event_queue.qsize()
            }
        }
        
        # Get repository stats (simplified)
        try:
            stats["repositories"]["active_sessions"] = len(
                self.repositories['session'].get_active_sessions(limit=1000)
            )
        except Exception:
            pass
        
        return stats


# Global data manager instance
data_manager = DataManager()


# Convenience functions for common operations
async def init_data_layer(**config):
    """Initialize the data layer"""
    await data_manager.initialize(config)


async def save_user(user: User) -> bool:
    """Save user with caching"""
    success = repositories['user'].save(user)
    if success:
        entity_cache.set_user(user)
    return success


async def save_session(session: Session) -> bool:
    """Save session with caching"""
    success = repositories['session'].save(session)
    if success:
        entity_cache.set_session(session)
    return success


async def save_story(story: Story) -> bool:
    """Save story with caching and analytics"""
    success = repositories['story'].save(story)
    if success:
        entity_cache.set_story(story)
        # Track analytics
        track_event(
            "story_saved",
            user_id=story.user_id,
            properties={
                "story_id": story.story_id,
                "style": story.style.value,
                "word_count": story.metrics["word_count"]
            }
        )
    return success


def get_user(user_id: str) -> Optional[User]:
    """Get user with caching"""
    # Try cache first
    user = entity_cache.get_user(user_id)
    if user:
        return user
    
    # Fall back to repository
    user = repositories['user'].get(user_id)
    if user:
        entity_cache.set_user(user)
    
    return user


def get_session(session_id: str) -> Optional[Session]:
    """Get session with caching"""
    # Try cache first
    session = entity_cache.get_session(session_id)
    if session:
        return session
    
    # Fall back to repository
    session = repositories['session'].get(session_id)
    if session:
        entity_cache.set_session(session)
    
    return session


def get_story(story_id: str) -> Optional[Story]:
    """Get story with caching"""
    # Try cache first
    story = entity_cache.get_story(story_id)
    if story:
        return story
    
    # Fall back to repository
    story = repositories['story'].get(story_id)
    if story:
        entity_cache.set_story(story)
    
    return story


# Export all public interfaces
__all__ = [
    # Models
    'User', 'Story', 'Session', 'Template', 'RichmondContent', 'Analytics',
    'UserRole', 'StoryStyle', 'StoryStatus', 'TemplateCategory',
    
    # Repositories
    'repositories', 'UserRepository', 'SessionRepository', 'StoryRepository',
    'TemplateRepository', 'RichmondContentRepository', 'AnalyticsRepository',
    
    # Cache
    'cache_manager', 'entity_cache', 'cache_decorator',
    
    # Pipeline
    'run_ingestion_pipeline',
    
    # Backup
    'create_backup', 'restore_from_backup', 'list_available_backups',
    
    # Analytics
    'track_event', 'track_api_call', 'get_analytics_dashboard', 'generate_report',
    
    # Migration
    'run_migration', 'verify_migration', 'export_in_memory_data',
    
    # Data manager
    'data_manager', 'init_data_layer',
    
    # Convenience functions
    'save_user', 'save_session', 'save_story',
    'get_user', 'get_session', 'get_story'
]