"""
Multi-layer caching implementation with Redis
Provides fast access to frequently used data with automatic invalidation
"""
import redis
import json
import pickle
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import logging
from dataclasses import asdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .models import User, Story, Session, Template, RichmondContent
from .dynamodb_schema import DynamoDBTables

logger = logging.getLogger('storygen.cache')


class CacheConfig:
    """Cache configuration and TTL settings"""
    
    # Redis connection settings
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    REDIS_SSL = False
    
    # TTL settings (in seconds)
    TTL_USER = 3600  # 1 hour
    TTL_SESSION = 1800  # 30 minutes
    TTL_STORY = 7200  # 2 hours
    TTL_TEMPLATE = 86400  # 24 hours
    TTL_CONTENT = 43200  # 12 hours
    TTL_VECTOR_SEARCH = 3600  # 1 hour
    TTL_API_RESPONSE = 300  # 5 minutes
    TTL_STATS = 60  # 1 minute
    
    # Cache key prefixes
    PREFIX_USER = "user"
    PREFIX_SESSION = "session"
    PREFIX_STORY = "story"
    PREFIX_TEMPLATE = "template"
    PREFIX_CONTENT = "content"
    PREFIX_VECTOR = "vector"
    PREFIX_API = "api"
    PREFIX_STATS = "stats"
    PREFIX_LOCK = "lock"
    
    # Cache warming settings
    WARM_ON_STARTUP = True
    WARM_BATCH_SIZE = 100
    WARM_PARALLEL_WORKERS = 4


class CacheManager:
    """Main cache manager with Redis backend"""
    
    def __init__(self, config: CacheConfig = CacheConfig()):
        self.config = config
        self._redis_client = None
        self._local_cache = {}  # L1 cache for ultra-fast access
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self._executor = ThreadPoolExecutor(max_workers=config.WARM_PARALLEL_WORKERS)
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client (lazy initialization)"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                password=self.config.REDIS_PASSWORD,
                ssl=self.config.REDIS_SSL,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            # Test connection
            try:
                self._redis_client.ping()
                logger.info("Connected to Redis cache")
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._redis_client
    
    def _make_key(self, prefix: str, *parts: str) -> str:
        """Create cache key from parts"""
        key_parts = [prefix] + [str(p) for p in parts if p]
        return ":".join(key_parts)
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if hasattr(value, 'to_dict'):
            # Handle our model objects
            return json.dumps(value.to_dict()).encode('utf-8')
        elif isinstance(value, (dict, list, str, int, float, bool)):
            # Handle JSON-serializable types
            return json.dumps(value).encode('utf-8')
        else:
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes, model_class: Optional[type] = None) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
        
        try:
            # Try JSON first
            value = json.loads(data.decode('utf-8'))
            
            # Convert to model object if class provided
            if model_class and hasattr(model_class, 'from_dict'):
                return model_class.from_dict(value)
            
            return value
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Failed to deserialize cache data: {e}")
                return None
    
    def get(self, key: str, model_class: Optional[type] = None) -> Optional[Any]:
        """Get value from cache"""
        try:
            # Check L1 cache first
            if key in self._local_cache:
                self._cache_stats["hits"] += 1
                return self._local_cache[key]
            
            # Check Redis
            data = self.redis.get(key)
            if data:
                value = self._deserialize(data, model_class)
                if value:
                    # Store in L1 cache
                    self._local_cache[key] = value
                    self._cache_stats["hits"] += 1
                    return value
            
            self._cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            self._cache_stats["errors"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        try:
            # Serialize value
            data = self._serialize(value)
            
            # Set in Redis with TTL
            if ttl:
                self.redis.setex(key, ttl, data)
            else:
                self.redis.set(key, data)
            
            # Update L1 cache
            self._local_cache[key] = value
            
            self._cache_stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            self._cache_stats["errors"] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            # Remove from L1 cache
            self._local_cache.pop(key, None)
            
            # Remove from Redis
            result = self.redis.delete(key) > 0
            
            self._cache_stats["deletes"] += 1
            return result
            
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            self._cache_stats["errors"] += 1
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            # Clear L1 cache entries matching pattern
            keys_to_remove = [k for k in self._local_cache.keys() if self._match_pattern(k, pattern)]
            for key in keys_to_remove:
                self._local_cache.pop(key, None)
            
            # Delete from Redis
            deleted = 0
            for key in self.redis.scan_iter(match=pattern):
                if self.redis.delete(key):
                    deleted += 1
            
            self._cache_stats["deletes"] += deleted
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            self._cache_stats["errors"] += 1
            return 0
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for L1 cache"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if key in self._local_cache:
            return True
        return bool(self.redis.exists(key))
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        try:
            return bool(self.redis.expire(key, ttl))
        except Exception as e:
            logger.error(f"Cache expire error for {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        try:
            ttl = self.redis.ttl(key)
            return ttl if ttl >= 0 else 0
        except Exception:
            return 0
    
    def mget(self, keys: List[str], model_class: Optional[type] = None) -> Dict[str, Any]:
        """Get multiple values at once"""
        try:
            # Check L1 cache first
            results = {}
            missing_keys = []
            
            for key in keys:
                if key in self._local_cache:
                    results[key] = self._local_cache[key]
                else:
                    missing_keys.append(key)
            
            # Get missing from Redis
            if missing_keys:
                values = self.redis.mget(missing_keys)
                for key, data in zip(missing_keys, values):
                    if data:
                        value = self._deserialize(data, model_class)
                        if value:
                            results[key] = value
                            self._local_cache[key] = value
            
            return results
            
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            return {}
    
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values at once"""
        try:
            # Serialize all values
            serialized = {}
            for key, value in mapping.items():
                data = self._serialize(value)
                serialized[key] = data
                self._local_cache[key] = value
            
            # Set in Redis
            if ttl:
                # Use pipeline for TTL
                pipe = self.redis.pipeline()
                for key, data in serialized.items():
                    pipe.setex(key, ttl, data)
                pipe.execute()
            else:
                self.redis.mset(serialized)
            
            self._cache_stats["sets"] += len(mapping)
            return True
            
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            self._cache_stats["errors"] += 1
            return False
    
    def clear_l1_cache(self):
        """Clear local L1 cache"""
        self._local_cache.clear()
        logger.info("Cleared L1 cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self._cache_stats.copy()
        stats["l1_size"] = len(self._local_cache)
        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"])
            if stats["hits"] + stats["misses"] > 0
            else 0
        )
        
        # Get Redis info
        try:
            redis_info = self.redis.info()
            stats["redis_used_memory"] = redis_info.get("used_memory_human", "N/A")
            stats["redis_connected_clients"] = redis_info.get("connected_clients", 0)
            stats["redis_total_commands"] = redis_info.get("total_commands_processed", 0)
        except Exception:
            pass
        
        return stats
    
    def reset_stats(self):
        """Reset cache statistics"""
        for key in self._cache_stats:
            self._cache_stats[key] = 0


class CacheDecorator:
    """Decorators for caching function results"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    def cached(self, prefix: str, ttl: int, key_func: Optional[Callable] = None):
        """Cache decorator for functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = self.cache._make_key(prefix, key_func(*args, **kwargs))
                else:
                    # Default key generation
                    key_parts = [str(arg) for arg in args]
                    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                    key_hash = hashlib.md5(":".join(key_parts).encode()).hexdigest()[:8]
                    cache_key = self.cache._make_key(prefix, func.__name__, key_hash)
                
                # Try to get from cache
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                if result is not None:
                    self.cache.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def invalidate(self, prefix: str, key_func: Optional[Callable] = None):
        """Invalidate cache decorator"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Execute function first
                result = func(*args, **kwargs)
                
                # Invalidate cache
                if key_func:
                    cache_key = self.cache._make_key(prefix, key_func(*args, **kwargs))
                    self.cache.delete(cache_key)
                else:
                    # Invalidate all keys with prefix
                    pattern = f"{prefix}:*"
                    self.cache.delete_pattern(pattern)
                
                return result
            
            return wrapper
        return decorator


class EntityCache:
    """High-level cache interface for entities"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.decorator = CacheDecorator(cache_manager)
    
    # User caching
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user from cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_USER, user_id)
        return self.cache.get(key, User)
    
    def set_user(self, user: User) -> bool:
        """Set user in cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_USER, user.user_id)
        return self.cache.set(key, user, CacheConfig.TTL_USER)
    
    def invalidate_user(self, user_id: str) -> bool:
        """Invalidate user cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_USER, user_id)
        return self.cache.delete(key)
    
    # Session caching
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session from cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_SESSION, session_id)
        return self.cache.get(key, Session)
    
    def set_session(self, session: Session) -> bool:
        """Set session in cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_SESSION, session.session_id)
        return self.cache.set(key, session, CacheConfig.TTL_SESSION)
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_SESSION, session_id)
        return self.cache.delete(key)
    
    # Story caching
    def get_story(self, story_id: str) -> Optional[Story]:
        """Get story from cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_STORY, story_id)
        return self.cache.get(key, Story)
    
    def set_story(self, story: Story) -> bool:
        """Set story in cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_STORY, story.story_id)
        return self.cache.set(key, story, CacheConfig.TTL_STORY)
    
    def invalidate_story(self, story_id: str) -> bool:
        """Invalidate story cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_STORY, story_id)
        return self.cache.delete(key)
    
    def invalidate_user_stories(self, user_id: str) -> int:
        """Invalidate all cached stories for a user"""
        pattern = f"{CacheConfig.PREFIX_STORY}:*"
        # This is a simplified version - in production, you'd track user-story relationships
        return self.cache.delete_pattern(pattern)
    
    # Template caching
    def get_template(self, template_id: str) -> Optional[Template]:
        """Get template from cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_TEMPLATE, template_id)
        return self.cache.get(key, Template)
    
    def set_template(self, template: Template) -> bool:
        """Set template in cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_TEMPLATE, template.template_id)
        return self.cache.set(key, template, CacheConfig.TTL_TEMPLATE)
    
    def invalidate_template(self, template_id: str) -> bool:
        """Invalidate template cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_TEMPLATE, template_id)
        return self.cache.delete(key)
    
    def get_template_list(self, list_key: str) -> Optional[List[Template]]:
        """Get cached template list"""
        key = self.cache._make_key(CacheConfig.PREFIX_TEMPLATE, "list", list_key)
        return self.cache.get(key)
    
    def set_template_list(self, list_key: str, templates: List[Template]) -> bool:
        """Cache template list"""
        key = self.cache._make_key(CacheConfig.PREFIX_TEMPLATE, "list", list_key)
        return self.cache.set(key, templates, CacheConfig.TTL_TEMPLATE)
    
    # Richmond content caching
    def get_content(self, content_id: str) -> Optional[RichmondContent]:
        """Get Richmond content from cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_CONTENT, content_id)
        return self.cache.get(key, RichmondContent)
    
    def set_content(self, content: RichmondContent) -> bool:
        """Set Richmond content in cache"""
        key = self.cache._make_key(CacheConfig.PREFIX_CONTENT, content.content_id)
        return self.cache.set(key, content, CacheConfig.TTL_CONTENT)
    
    def get_content_batch(self, content_ids: List[str]) -> Dict[str, RichmondContent]:
        """Get multiple content items from cache"""
        keys = [self.cache._make_key(CacheConfig.PREFIX_CONTENT, cid) for cid in content_ids]
        results = self.cache.mget(keys, RichmondContent)
        
        # Map back to content IDs
        mapped = {}
        for cid, key in zip(content_ids, keys):
            if key in results:
                mapped[cid] = results[key]
        
        return mapped
    
    def set_content_batch(self, contents: List[RichmondContent]) -> bool:
        """Set multiple content items in cache"""
        mapping = {}
        for content in contents:
            key = self.cache._make_key(CacheConfig.PREFIX_CONTENT, content.content_id)
            mapping[key] = content
        
        return self.cache.mset(mapping, CacheConfig.TTL_CONTENT)
    
    # Vector search result caching
    def get_vector_results(self, query: str, limit: int = 5) -> Optional[List[str]]:
        """Get cached vector search results"""
        query_hash = hashlib.md5(f"{query}:{limit}".encode()).hexdigest()[:16]
        key = self.cache._make_key(CacheConfig.PREFIX_VECTOR, query_hash)
        return self.cache.get(key)
    
    def set_vector_results(self, query: str, limit: int, results: List[str]) -> bool:
        """Cache vector search results"""
        query_hash = hashlib.md5(f"{query}:{limit}".encode()).hexdigest()[:16]
        key = self.cache._make_key(CacheConfig.PREFIX_VECTOR, query_hash)
        return self.cache.set(key, results, CacheConfig.TTL_VECTOR_SEARCH)
    
    # API response caching
    def get_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Get cached API response"""
        param_str = json.dumps(params, sort_keys=True)
        response_hash = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()[:16]
        key = self.cache._make_key(CacheConfig.PREFIX_API, endpoint.replace("/", "_"), response_hash)
        return self.cache.get(key)
    
    def set_api_response(self, endpoint: str, params: Dict[str, Any], response: Dict) -> bool:
        """Cache API response"""
        param_str = json.dumps(params, sort_keys=True)
        response_hash = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()[:16]
        key = self.cache._make_key(CacheConfig.PREFIX_API, endpoint.replace("/", "_"), response_hash)
        return self.cache.set(key, response, CacheConfig.TTL_API_RESPONSE)
    
    # Stats caching
    def get_stats(self, stat_type: str) -> Optional[Dict]:
        """Get cached statistics"""
        key = self.cache._make_key(CacheConfig.PREFIX_STATS, stat_type)
        return self.cache.get(key)
    
    def set_stats(self, stat_type: str, stats: Dict) -> bool:
        """Cache statistics"""
        key = self.cache._make_key(CacheConfig.PREFIX_STATS, stat_type)
        return self.cache.set(key, stats, CacheConfig.TTL_STATS)


class CacheWarmer:
    """Warm cache with frequently accessed data"""
    
    def __init__(self, cache_manager: CacheManager, repositories: Dict[str, Any]):
        self.cache = cache_manager
        self.entity_cache = EntityCache(cache_manager)
        self.repositories = repositories
    
    async def warm_cache(self):
        """Warm cache with initial data"""
        logger.info("Starting cache warming...")
        
        tasks = [
            self._warm_templates(),
            self._warm_active_sessions(),
            self._warm_recent_stories(),
            self._warm_richmond_content()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Cache warming task {i} failed: {result}")
        
        logger.info("Cache warming completed")
    
    async def _warm_templates(self):
        """Warm template cache"""
        try:
            templates = self.repositories['template'].list_public_templates(limit=50)
            for template in templates:
                self.entity_cache.set_template(template)
            
            # Cache the list as well
            self.entity_cache.set_template_list("public", templates)
            
            logger.info(f"Warmed cache with {len(templates)} templates")
        except Exception as e:
            logger.error(f"Failed to warm template cache: {e}")
    
    async def _warm_active_sessions(self):
        """Warm active session cache"""
        try:
            sessions = self.repositories['session'].get_active_sessions(limit=100)
            for session in sessions:
                self.entity_cache.set_session(session)
            
            logger.info(f"Warmed cache with {len(sessions)} active sessions")
        except Exception as e:
            logger.error(f"Failed to warm session cache: {e}")
    
    async def _warm_recent_stories(self):
        """Warm recent stories cache"""
        try:
            # Get recent published stories
            from .models import StoryStatus
            stories = self.repositories['story'].list_by_status(
                StoryStatus.PUBLISHED, 
                limit=50
            )
            for story in stories:
                self.entity_cache.set_story(story)
            
            logger.info(f"Warmed cache with {len(stories)} recent stories")
        except Exception as e:
            logger.error(f"Failed to warm story cache: {e}")
    
    async def _warm_richmond_content(self):
        """Warm Richmond content cache"""
        try:
            # Cache frequently used content types
            for content_type in ["quotes", "culture", "economy"]:
                contents = self.repositories['content'].list_by_type(
                    content_type, 
                    limit=20
                )
                self.entity_cache.set_content_batch(contents)
            
            logger.info("Warmed cache with Richmond content")
        except Exception as e:
            logger.error(f"Failed to warm content cache: {e}")


# Global cache instances
cache_manager = CacheManager()
entity_cache = EntityCache(cache_manager)
cache_decorator = CacheDecorator(cache_manager)