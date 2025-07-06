# Data Architecture Documentation

## Overview

The Richmond Storyline Generator data layer provides a comprehensive, scalable solution for data persistence, caching, analytics, and management. This document details the architecture, components, and usage patterns.

## Architecture Components

### 1. Data Models (`data/models.py`)

Comprehensive data models with full validation and serialization:

- **User**: User profiles with preferences and statistics
- **Session**: Conversation sessions with full history
- **Story**: Generated stories with metrics and versions
- **Template**: Reusable story templates
- **RichmondContent**: Vector-indexed Richmond context
- **Analytics**: Event tracking for insights

### 2. DynamoDB Schema (`data/dynamodb_schema.py`)

Single-table design with Global Secondary Indexes (GSIs) for efficient queries:

**Main Table Structure:**
- Partition Key: `pk` (entity type + ID)
- Sort Key: `sk` (metadata/content/version)
- GSIs for user queries, status filtering, content types

**Benefits:**
- Cost-effective single-table design
- Efficient query patterns
- Built-in TTL for session expiration
- Point-in-time recovery support

### 3. Repository Pattern (`data/repositories.py`)

Clean data access layer with CRUD operations:

```python
# Example usage
user_repo = UserRepository()
user = User(email="user@example.com", username="richmondwriter")
success = user_repo.save(user)

# Complex queries
active_stories = story_repo.get_user_stories(
    user_id="user123",
    status=StoryStatus.PUBLISHED,
    limit=50
)
```

### 4. Multi-Layer Caching (`data/cache.py`)

High-performance caching with Redis:

**Cache Layers:**
1. **L1 Cache**: In-memory for ultra-fast access
2. **L2 Cache**: Redis for distributed caching
3. **Automatic invalidation**: Keep data consistent

**Cache Decorators:**
```python
@cache_decorator.cached("api_response", ttl=300)
def get_expensive_data(param):
    # This result will be cached for 5 minutes
    return expensive_operation(param)
```

### 5. Data Pipeline (`data/pipeline.py`)

Intelligent content ingestion and processing:

**Features:**
- Smart chunking strategies by content type
- Parallel embedding generation
- Pinecone vector indexing
- Progress monitoring
- Incremental updates

**Usage:**
```python
# Run full pipeline
results = await run_ingestion_pipeline("data/richmond_docs")

# Update single file
pipeline = DataPipeline()
await pipeline.update_content(Path("data/richmond_news.md"))
```

### 6. Backup System (`data/backup.py`)

Automated backup and disaster recovery:

**Backup Types:**
- Daily backups (2 AM)
- Weekly backups (Sundays)
- Monthly backups (1st of month)
- On-demand backups

**Features:**
- S3 storage with encryption
- Compression for efficiency
- Point-in-time recovery
- Automated retention management

### 7. Analytics Engine (`data/analytics_engine.py`)

Comprehensive analytics and reporting:

**Tracked Events:**
- User behavior (login, signup, engagement)
- Story metrics (generation time, tokens, publishing)
- API performance (response times, errors)
- Feature usage (voice, templates, search)

**Reports:**
- Real-time dashboards
- Daily/weekly summaries
- Funnel analysis
- User journey tracking

### 8. Migration Tools (`data/migration.py`)

Seamless data migration with validation:

**Features:**
- In-memory to DynamoDB migration
- Data validation and transformation
- Progress tracking with checkpoints
- Rollback support
- Dry-run mode

## Implementation Guide

### Initial Setup

1. **Environment Variables:**
```bash
export AWS_REGION=us-east-1
export PINECONE_API_KEY=your-key
export REDIS_HOST=localhost
```

2. **Initialize Data Layer:**
```python
from data import init_data_layer

await init_data_layer(
    create_tables=True,
    warm_cache=True,
    enable_backups=True
)
```

3. **Run Initial Data Ingestion:**
```python
from data import run_ingestion_pipeline

results = await run_ingestion_pipeline("data/richmond_docs")
print(f"Processed {results['stats']['files_processed']} files")
```

### Common Operations

#### User Management
```python
from data import save_user, get_user
from data.models import User, UserRole

# Create user
user = User(
    email="john@example.com",
    username="john_richmond",
    role=UserRole.REGISTERED
)
await save_user(user)

# Retrieve user
user = get_user(user.user_id)

# Update stats
user_repo.update_stats(user.user_id, {
    "stories_created": 1,
    "total_words": 500
})
```

#### Session Management
```python
from data import save_session, get_session
from session_manager import Session

# Create session
session = Session(user_id=user.user_id)
session.add_turn("kickoff", user_input="Tell Richmond's tech story")
await save_session(session)

# Retrieve session
session = get_session(session.session_id)

# Get active sessions
active = session_repo.get_active_sessions()
```

#### Story Operations
```python
from data import save_story, get_story
from data.models import Story, StoryStyle

# Create story
story = Story(
    user_id=user.user_id,
    session_id=session.session_id,
    content="Richmond's tech renaissance...",
    style=StoryStyle.SHORT_POST
)
await save_story(story)

# Update status
story_repo.update_status(story.story_id, StoryStatus.PUBLISHED)

# Get user's stories
stories = story_repo.get_user_stories(user.user_id)
```

#### Analytics Tracking
```python
from data import track_event, track_api_call

# Track custom event
track_event(
    "feature_used",
    user_id=user.user_id,
    properties={"feature": "voice_input"}
)

# Track API performance
track_api_call(
    endpoint="/generate-story",
    method="POST",
    status_code=200,
    response_time=1.23
)

# Get analytics dashboard
dashboard = get_analytics_dashboard("24h")
```

### Cache Patterns

#### Read-Through Cache
```python
def get_story_with_cache(story_id: str) -> Story:
    # Check cache first
    story = entity_cache.get_story(story_id)
    if story:
        return story
    
    # Load from database
    story = story_repo.get(story_id)
    if story:
        entity_cache.set_story(story)
    
    return story
```

#### Cache Invalidation
```python
def update_story(story_id: str, updates: dict):
    # Update database
    story_repo.update(story_id, updates)
    
    # Invalidate cache
    entity_cache.invalidate_story(story_id)
    
    # Invalidate related caches
    entity_cache.invalidate_user_stories(story.user_id)
```

### Backup and Recovery

#### Manual Backup
```python
from data import create_backup, list_available_backups

# Create backup
backup_result = await create_backup("manual")
print(f"Backup created: {backup_result['backup_id']}")

# List backups
backups = list_available_backups()
for backup in backups:
    print(f"{backup['backup_id']} - {backup['timestamp']}")
```

#### Restore from Backup
```python
from data import restore_from_backup

# Restore specific backup
result = await restore_from_backup(
    backup_id="daily_20240115_020000",
    tables=["storygen-main"],  # Selective restore
    create_tables=False
)
```

### Migration Process

#### Export Current Data
```python
from data import export_in_memory_data

# Export in-memory data
export_result = export_in_memory_data("migration_export")
print(f"Exported to: {export_result['output_directory']}")
```

#### Run Migration
```python
from data import run_migration
from data.migration import MigrationConfig

# Configure migration
config = MigrationConfig(
    source_type="in_memory",
    dry_run=True,  # Test first
    create_backup=True,
    validate_data=True
)

# Run migration
result = await run_migration(config)
print(f"Migrated {result['items_migrated']} items")
```

## Performance Optimization

### 1. Batch Operations
```python
# Batch save Richmond content
contents = [RichmondContent(...) for _ in range(100)]
saved_count = content_repo.save_batch(contents)

# Batch cache operations
entity_cache.set_content_batch(contents)
```

### 2. Query Optimization
```python
# Use GSIs for efficient queries
stories = story_repo.get_user_stories(
    user_id="user123",
    status=StoryStatus.PUBLISHED,
    limit=20  # Pagination
)

# Use projections to reduce data transfer
minimal_stories = story_repo.list_story_summaries(user_id)
```

### 3. Cache Warming
```python
# Warm cache on startup
warmer = CacheWarmer(cache_manager, repositories)
await warmer.warm_cache()

# Selective cache warming
await warmer._warm_templates()  # Just templates
```

## Monitoring and Maintenance

### Health Checks
```python
from data import data_manager

# Get health status
health = data_manager.get_health_status()
print(f"DynamoDB: {health['components']['dynamodb']}")
print(f"Redis: {health['components']['redis']}")
```

### Performance Monitoring
```python
# Get cache statistics
stats = cache_manager.get_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")

# Get analytics summary
summary = analytics_processor.get_dashboard_metrics("24h")
print(f"Active users: {summary['user_metrics']['active_users']}")
```

### Maintenance Tasks
```python
# Clean up expired sessions
expired = session_repo.cleanup_expired_sessions()

# Optimize cache
cache_manager.clear_l1_cache()

# Compact vector index
vector_manager.optimize_index()
```

## Security Considerations

1. **Encryption**: All backups encrypted with AES256
2. **Access Control**: Repository pattern enforces access rules
3. **Data Validation**: All input validated before storage
4. **Audit Trail**: Analytics tracks all data access
5. **PII Protection**: User data properly isolated

## Troubleshooting

### Common Issues

1. **Cache Misses**
   - Check Redis connection
   - Verify TTL settings
   - Monitor cache size

2. **Slow Queries**
   - Check GSI usage
   - Implement pagination
   - Add caching layer

3. **Migration Failures**
   - Check validation errors
   - Verify data formats
   - Use dry-run mode

4. **Backup Issues**
   - Verify S3 permissions
   - Check storage limits
   - Monitor backup logs

## Best Practices

1. **Always use repositories** for data access
2. **Cache frequently accessed data** with appropriate TTLs
3. **Track important events** for analytics
4. **Regular backups** with tested restore procedures
5. **Monitor performance** and optimize queries
6. **Validate data** before storage
7. **Use batch operations** for bulk updates
8. **Implement retry logic** for transient failures

## Future Enhancements

1. **GraphQL API** for flexible queries
2. **Real-time subscriptions** with DynamoDB Streams
3. **Advanced analytics** with machine learning
4. **Multi-region replication** for global scale
5. **Automated performance tuning**
6. **Enhanced security** with field-level encryption