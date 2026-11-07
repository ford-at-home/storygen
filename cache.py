"""
Redis caching layer for StoryGen
Handles caching strategies, invalidation, and distributed cache
"""

import json
import pickle
import hashlib
import functools
import time
from typing import Any, Optional, Callable, Union, Dict
from datetime import timedelta
import redis
from redis.sentinel import Sentinel
from redis.exceptions import RedisError
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


@dataclass
class CacheConfig:
    """Redis cache configuration"""
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    
    # Pool settings
    max_connections: int = 50
    connection_pool_kwargs: Dict[str, Any] = None
    
    # Sentinel settings (for HA)
    use_sentinel: bool = False
    sentinel_hosts: list = None
    sentinel_service_name: str = "mymaster"
    
    # Cache settings
    default_ttl: int = 3600  # 1 hour
    key_prefix: str = "storygen"
    serializer: str = "json"  # json or pickle
    
    # Feature flags
    enable_compression: bool = True
    enable_stats: bool = True
    enable_distributed_lock: bool = True
    
    def __post_init__(self):
        if self.connection_pool_kwargs is None:
            self.connection_pool_kwargs = {}
        if self.sentinel_hosts is None:
            self.sentinel_hosts = []


class RedisCache:
    """Production-ready Redis cache with advanced features"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._redis_client = None
        self._sentinel = None
        self._stats = CacheStats() if config.enable_stats else None
        
    @property
    def redis(self):
        """Lazy Redis connection initialization"""
        if self._redis_client is None:
            self._connect()
        return self._redis_client
        
    def _connect(self):
        """Establish Redis connection"""
        try:
            if self.config.use_sentinel:
                # High availability setup with Sentinel
                self._sentinel = Sentinel(
                    self.config.sentinel_hosts,
                    socket_connect_timeout=0.1,
                    **self.config.connection_pool_kwargs
                )
                self._redis_client = self._sentinel.master_for(
                    self.config.sentinel_service_name,
                    socket_timeout=0.1,
                    password=self.config.password,
                    db=self.config.db
                )
            else:
                # Standard Redis connection
                pool = redis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    decode_responses=False,
                    **self.config.connection_pool_kwargs
                )
                self._redis_client = redis.Redis(connection_pool=pool)
                
            # Test connection
            self._redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key"""
        return f"{self.config.key_prefix}:{key}"
        
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if self.config.serializer == "pickle":
            serialized = pickle.dumps(value)
        else:
            serialized = json.dumps(value).encode('utf-8')
            
        if self.config.enable_compression:
            import zlib
            serialized = zlib.compress(serialized)
            
        return serialized
        
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None
            
        if self.config.enable_compression:
            import zlib
            value = zlib.decompress(value)
            
        if self.config.serializer == "pickle":
            return pickle.loads(value)
        else:
            return json.loads(value.decode('utf-8'))
            
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        full_key = self._make_key(key)
        
        try:
            value = self.redis.get(full_key)
            
            if self._stats:
                if value is None:
                    self._stats.record_miss()
                else:
                    self._stats.record_hit()
                    
            return self._deserialize(value)
            
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            if self._stats:
                self._stats.record_error()
            return None
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        full_key = self._make_key(key)
        ttl = ttl or self.config.default_ttl
        
        try:
            serialized = self._serialize(value)
            result = self.redis.setex(full_key, ttl, serialized)
            
            if self._stats:
                self._stats.record_set()
                
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            if self._stats:
                self._stats.record_error()
            return False
            
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        full_key = self._make_key(key)
        
        try:
            result = self.redis.delete(full_key)
            
            if self._stats:
                self._stats.record_delete()
                
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            if self._stats:
                self._stats.record_error()
            return False
            
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        full_key = self._make_key(key)
        
        try:
            return bool(self.redis.exists(full_key))
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
            
    def get_many(self, keys: list) -> Dict[str, Any]:
        """Get multiple values at once"""
        full_keys = [self._make_key(k) for k in keys]
        
        try:
            values = self.redis.mget(full_keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
                    
            if self._stats:
                hits = len([v for v in values if v is not None])
                misses = len(values) - hits
                self._stats.record_multi_operation(hits, misses)
                
            return result
            
        except RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            if self._stats:
                self._stats.record_error()
            return {}
            
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values at once"""
        ttl = ttl or self.config.default_ttl
        
        try:
            pipe = self.redis.pipeline()
            
            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value)
                pipe.setex(full_key, ttl, serialized)
                
            results = pipe.execute()
            
            if self._stats:
                self._stats.record_multi_set(len(mapping))
                
            return all(results)
            
        except RedisError as e:
            logger.error(f"Redis MSET error: {e}")
            if self._stats:
                self._stats.record_error()
            return False
            
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomic increment operation"""
        full_key = self._make_key(key)
        
        try:
            return self.redis.incrby(full_key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None
            
    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomic decrement operation"""
        full_key = self._make_key(key)
        
        try:
            return self.redis.decrby(full_key, amount)
        except RedisError as e:
            logger.error(f"Redis DECR error for key {key}: {e}")
            return None
            
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        full_key = self._make_key(key)
        
        try:
            return bool(self.redis.expire(full_key, ttl))
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
            
    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        full_pattern = self._make_key(pattern)
        
        try:
            keys = list(self.redis.scan_iter(match=full_pattern))
            if keys:
                return self.redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis pattern delete error: {e}")
            return 0
            
    def distributed_lock(self, lock_name: str, timeout: int = 10) -> 'DistributedLock':
        """Get distributed lock for coordinating operations"""
        if not self.config.enable_distributed_lock:
            raise ValueError("Distributed locks are disabled")
            
        return DistributedLock(self.redis, self._make_key(f"lock:{lock_name}"), timeout)
        
    def get_stats(self) -> Optional['CacheStats']:
        """Get cache statistics"""
        return self._stats
        
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            return self.redis.ping()
        except:
            return False


class CacheStats:
    """Track cache statistics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.start_time = time.time()
        
    def record_hit(self):
        self.hits += 1
        
    def record_miss(self):
        self.misses += 1
        
    def record_set(self):
        self.sets += 1
        
    def record_delete(self):
        self.deletes += 1
        
    def record_error(self):
        self.errors += 1
        
    def record_multi_operation(self, hits: int, misses: int):
        self.hits += hits
        self.misses += misses
        
    def record_multi_set(self, count: int):
        self.sets += count
        
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
        
    @property
    def uptime(self) -> float:
        return time.time() - self.start_time
        
    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.2f}%",
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "uptime_seconds": int(self.uptime)
        }


class DistributedLock:
    """Distributed lock implementation using Redis"""
    
    def __init__(self, redis_client: redis.Redis, key: str, timeout: int):
        self.redis = redis_client
        self.key = key
        self.timeout = timeout
        self.identifier = None
        
    def __enter__(self):
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        
    def acquire(self, blocking: bool = True, timeout: Optional[int] = None) -> bool:
        """Acquire the lock"""
        import uuid
        
        self.identifier = str(uuid.uuid4())
        timeout = timeout or self.timeout
        
        if blocking:
            while True:
                if self.redis.set(self.key, self.identifier, nx=True, ex=timeout):
                    return True
                time.sleep(0.001)
        else:
            return bool(self.redis.set(self.key, self.identifier, nx=True, ex=timeout))
            
    def release(self) -> bool:
        """Release the lock"""
        if self.identifier is None:
            return False
            
        # Lua script for atomic release
        lua_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis.eval(lua_script, 1, self.key, self.identifier)
            return bool(result)
        except RedisError:
            return False
        finally:
            self.identifier = None


# Caching decorators
def cached(cache: RedisCache, key_pattern: str, ttl: Optional[int] = None, 
          strategy: CacheStrategy = CacheStrategy.TTL):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key_pattern.format(
                func_name=func.__name__,
                args=hashlib.md5(str(args).encode()).hexdigest(),
                kwargs=hashlib.md5(str(kwargs).encode()).hexdigest()
            )
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
                
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")
                
            return result
            
        return wrapper
    return decorator


def invalidate_cache(cache: RedisCache, pattern: str):
    """Decorator to invalidate cache entries matching pattern"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache entries
            deleted = cache.clear_pattern(pattern)
            logger.debug(f"Invalidated {deleted} cache entries matching {pattern}")
            
            return result
            
        return wrapper
    return decorator


# Initialize global cache instance
cache_config = CacheConfig(
    host="redis",
    port=6379,
    default_ttl=3600,
    enable_compression=True,
    enable_stats=True
)
cache = RedisCache(cache_config)