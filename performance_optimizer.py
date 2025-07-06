"""
Performance Optimizer for Richmond Storyline Generator
Ensures the system meets performance requirements
"""

import time
import asyncio
import functools
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import redis
from prometheus_client import Histogram, Counter, Gauge
import cachetools
from cache import CacheManager

logger = logging.getLogger(__name__)


# Metrics
REQUEST_DURATION = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method']
)

CACHE_HIT_COUNTER = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISS_COUNTER = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

CONCURRENT_REQUESTS = Gauge(
    'concurrent_requests',
    'Number of concurrent requests being processed'
)


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    # Caching
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    max_cache_size: int = 1000
    
    # Connection pooling
    redis_pool_size: int = 50
    redis_pool_timeout: int = 20
    
    # Concurrency
    max_workers: int = 10
    use_process_pool: bool = False
    
    # Request optimization
    enable_compression: bool = True
    enable_request_batching: bool = True
    batch_size: int = 10
    batch_timeout: float = 0.1
    
    # Resource limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 30
    max_concurrent_requests: int = 100


class PerformanceOptimizer:
    """Main performance optimization class"""
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        
        # Initialize caches
        self._init_caches()
        
        # Initialize thread/process pools
        self._init_pools()
        
        # Initialize Redis connection pool
        self._init_redis_pool()
        
        # Request batching
        self.pending_requests: Dict[str, List] = {}
        self.batch_locks: Dict[str, asyncio.Lock] = {}
    
    def _init_caches(self):
        """Initialize various cache layers"""
        # In-memory LRU cache for hot data
        self.memory_cache = cachetools.LRUCache(maxsize=self.config.max_cache_size)
        
        # TTL cache for time-sensitive data
        self.ttl_cache = cachetools.TTLCache(
            maxsize=self.config.max_cache_size,
            ttl=self.config.cache_ttl
        )
        
        # Redis cache manager for distributed caching
        self.redis_cache = CacheManager()
    
    def _init_pools(self):
        """Initialize thread and process pools"""
        if self.config.use_process_pool:
            self.executor = ProcessPoolExecutor(max_workers=self.config.max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    def _init_redis_pool(self):
        """Initialize Redis connection pool"""
        self.redis_pool = redis.ConnectionPool(
            host='localhost',
            port=6379,
            max_connections=self.config.redis_pool_size,
            socket_connect_timeout=self.config.redis_pool_timeout,
            socket_timeout=self.config.redis_pool_timeout,
            decode_responses=True
        )
    
    def cache_result(self, cache_key: str, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if callable(cache_key):
                    key = cache_key(*args, **kwargs)
                else:
                    key = cache_key
                
                # Check memory cache first
                if key in self.memory_cache:
                    CACHE_HIT_COUNTER.labels(cache_type='memory').inc()
                    return self.memory_cache[key]
                
                # Check Redis cache
                cached_value = self.redis_cache.get(key)
                if cached_value is not None:
                    CACHE_HIT_COUNTER.labels(cache_type='redis').inc()
                    self.memory_cache[key] = cached_value
                    return cached_value
                
                # Cache miss - execute function
                CACHE_MISS_COUNTER.labels(cache_type='all').inc()
                result = func(*args, **kwargs)
                
                # Store in both caches
                self.memory_cache[key] = result
                self.redis_cache.set(key, result, ttl=ttl or self.config.cache_ttl)
                
                return result
            
            # Add async version if original is async
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    # Similar logic but async
                    if callable(cache_key):
                        key = cache_key(*args, **kwargs)
                    else:
                        key = cache_key
                    
                    # Check caches
                    if key in self.memory_cache:
                        CACHE_HIT_COUNTER.labels(cache_type='memory').inc()
                        return self.memory_cache[key]
                    
                    cached_value = await asyncio.get_event_loop().run_in_executor(
                        None, self.redis_cache.get, key
                    )
                    
                    if cached_value is not None:
                        CACHE_HIT_COUNTER.labels(cache_type='redis').inc()
                        self.memory_cache[key] = cached_value
                        return cached_value
                    
                    # Execute async function
                    CACHE_MISS_COUNTER.labels(cache_type='all').inc()
                    result = await func(*args, **kwargs)
                    
                    # Store in caches
                    self.memory_cache[key] = result
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.redis_cache.set, key, result, ttl or self.config.cache_ttl
                    )
                    
                    return result
                
                return async_wrapper
            
            return wrapper
        return decorator
    
    def measure_performance(self, endpoint: str, method: str = "GET"):
        """Decorator to measure function performance"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                CONCURRENT_REQUESTS.inc()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)
                    CONCURRENT_REQUESTS.dec()
                    
                    if duration > 1.0:
                        logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")
            
            # Async version
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    CONCURRENT_REQUESTS.inc()
                    
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)
                        CONCURRENT_REQUESTS.dec()
                        
                        if duration > 1.0:
                            logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")
                
                return async_wrapper
            
            return wrapper
        return decorator
    
    async def batch_requests(self, batch_key: str, request_data: Any, 
                           processor: Callable) -> Any:
        """Batch multiple requests together for processing"""
        if not self.config.enable_request_batching:
            return await processor([request_data])
        
        # Initialize batch lock if needed
        if batch_key not in self.batch_locks:
            self.batch_locks[batch_key] = asyncio.Lock()
        
        # Add request to pending batch
        if batch_key not in self.pending_requests:
            self.pending_requests[batch_key] = []
        
        self.pending_requests[batch_key].append(request_data)
        
        # Process batch if size reached or timeout
        if len(self.pending_requests[batch_key]) >= self.config.batch_size:
            async with self.batch_locks[batch_key]:
                if batch_key in self.pending_requests:
                    batch = self.pending_requests.pop(batch_key)
                    return await processor(batch)
        else:
            # Wait for batch timeout
            await asyncio.sleep(self.config.batch_timeout)
            
            async with self.batch_locks[batch_key]:
                if batch_key in self.pending_requests and self.pending_requests[batch_key]:
                    batch = self.pending_requests.pop(batch_key)
                    return await processor(batch)
        
        return None
    
    def optimize_database_query(self, query: str) -> str:
        """Optimize database queries"""
        # Add query optimization logic
        optimized = query
        
        # Example optimizations
        if "SELECT *" in query:
            logger.warning("Query uses SELECT * - consider specifying columns")
        
        if "ORDER BY" not in query and "LIMIT" in query:
            logger.warning("LIMIT without ORDER BY may return inconsistent results")
        
        return optimized
    
    def get_connection_from_pool(self) -> redis.Redis:
        """Get Redis connection from pool"""
        return redis.Redis(connection_pool=self.redis_pool)
    
    async def parallel_process(self, items: List[Any], processor: Callable, 
                             max_concurrent: Optional[int] = None) -> List[Any]:
        """Process items in parallel with concurrency control"""
        max_concurrent = max_concurrent or self.config.max_workers
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(processor):
                    return await processor(item)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(self.executor, processor, item)
        
        tasks = [process_with_semaphore(item) for item in items]
        return await asyncio.gather(*tasks)
    
    def preload_cache(self, cache_keys: List[str], data_loader: Callable):
        """Preload cache with frequently accessed data"""
        logger.info(f"Preloading {len(cache_keys)} cache entries...")
        
        for key in cache_keys:
            if key not in self.memory_cache:
                try:
                    data = data_loader(key)
                    self.memory_cache[key] = data
                    self.redis_cache.set(key, data)
                except Exception as e:
                    logger.error(f"Failed to preload cache key {key}: {e}")
        
        logger.info("Cache preloading completed")
    
    def optimize_memory_usage(self):
        """Optimize memory usage by clearing old cache entries"""
        import gc
        
        # Clear expired entries from TTL cache
        self.ttl_cache.expire()
        
        # Trigger garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        
        # Log memory usage
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        return {
            "cache_stats": {
                "memory_cache_size": len(self.memory_cache),
                "memory_cache_hits": self.memory_cache.hits if hasattr(self.memory_cache, 'hits') else 0,
                "memory_cache_misses": self.memory_cache.misses if hasattr(self.memory_cache, 'misses') else 0,
            },
            "concurrent_requests": CONCURRENT_REQUESTS._value.get(),
            "pool_stats": {
                "executor_type": type(self.executor).__name__,
                "max_workers": self.config.max_workers,
            },
            "redis_pool_stats": {
                "created_connections": self.redis_pool.created_connections,
                "available_connections": len(self.redis_pool._available_connections),
                "in_use_connections": len(self.redis_pool._in_use_connections),
            }
        }


# Global optimizer instance
_optimizer: Optional[PerformanceOptimizer] = None


def get_optimizer(config: Optional[PerformanceConfig] = None) -> PerformanceOptimizer:
    """Get or create the global optimizer instance"""
    global _optimizer
    
    if _optimizer is None:
        _optimizer = PerformanceOptimizer(config)
    
    return _optimizer


# Convenience decorators
def cached(cache_key: str, ttl: Optional[int] = None):
    """Convenience decorator for caching"""
    optimizer = get_optimizer()
    return optimizer.cache_result(cache_key, ttl)


def measured(endpoint: str, method: str = "GET"):
    """Convenience decorator for performance measurement"""
    optimizer = get_optimizer()
    return optimizer.measure_performance(endpoint, method)


# Example optimized functions
@cached(lambda text: f"embeddings:{hash(text)}", ttl=86400)
def get_embeddings(text: str) -> List[float]:
    """Get embeddings with caching"""
    # Expensive embedding generation
    import time
    time.sleep(0.1)  # Simulate API call
    return [0.1] * 1536  # Mock embeddings


@measured("/api/generate-story", "POST")
async def optimized_story_generation(core_idea: str, style: str) -> str:
    """Optimized story generation with performance tracking"""
    optimizer = get_optimizer()
    
    # Check cache first
    cache_key = f"story:{core_idea}:{style}"
    
    @cached(cache_key, ttl=3600)
    async def generate():
        # Actual generation logic
        return f"Generated story for {core_idea} in {style} style"
    
    return await generate()


if __name__ == "__main__":
    # Test performance optimizer
    import asyncio
    
    async def test_optimizer():
        optimizer = get_optimizer()
        
        # Test caching
        result1 = get_embeddings("test text")
        result2 = get_embeddings("test text")  # Should be cached
        
        # Test parallel processing
        items = list(range(10))
        results = await optimizer.parallel_process(
            items,
            lambda x: x * 2,
            max_concurrent=3
        )
        print(f"Parallel results: {results}")
        
        # Get performance report
        report = optimizer.get_performance_report()
        print(f"Performance report: {report}")
    
    asyncio.run(test_optimizer())