"""
Rate Limiting and API Security for Richmond Storyline Generator
Comprehensive rate limiting, DDoS protection, and API security controls
"""

import time
import hashlib
import redis
import logging
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limiting configuration"""
    
    # Default rate limits (requests per time window)
    DEFAULT_LIMITS = {
        'minute': 60,      # 60 requests per minute
        'hour': 1000,      # 1000 requests per hour
        'day': 10000       # 10000 requests per day
    }
    
    # Strict limits for sensitive endpoints
    STRICT_LIMITS = {
        'minute': 5,       # 5 requests per minute
        'hour': 50,        # 50 requests per hour
        'day': 200         # 200 requests per day
    }
    
    # Authentication limits
    AUTH_LIMITS = {
        'minute': 3,       # 3 auth attempts per minute
        'hour': 10,        # 10 auth attempts per hour
        'day': 50          # 50 auth attempts per day
    }
    
    # File upload limits
    UPLOAD_LIMITS = {
        'minute': 2,       # 2 uploads per minute
        'hour': 10,        # 10 uploads per hour
        'day': 50          # 50 uploads per day
    }
    
    # Time windows in seconds
    TIME_WINDOWS = {
        'minute': 60,
        'hour': 3600,
        'day': 86400
    }


class RateLimiter:
    """Redis-based rate limiter with multiple strategies"""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self.fallback_storage = {}
        self.blocked_ips = set()
        
        # Initialize Redis connection
        self._init_redis(redis_url)
    
    def _init_redis(self, redis_url: str = None):
        """Initialize Redis connection"""
        try:
            if not redis_url:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/2')
            
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis rate limiter connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️  Using in-memory rate limiting (not recommended for production)")
            self.redis_client = None
    
    def _get_client_key(self, identifier: str = None) -> str:
        """Get client identifier for rate limiting"""
        if identifier:
            return identifier
        
        # Try to get the most accurate client identifier
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            # Handle comma-separated IPs from proxies
            client_ip = client_ip.split(',')[0].strip()
        
        user_agent = request.headers.get('User-Agent', '')
        
        # Create a hash to anonymize while maintaining uniqueness
        client_key = hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
        
        return client_key
    
    def _get_rate_limit_key(self, client_key: str, endpoint: str, window: str) -> str:
        """Generate rate limit key"""
        return f"rate_limit:{client_key}:{endpoint}:{window}"
    
    def check_rate_limit(self, endpoint: str, limits: Dict[str, int], 
                        client_key: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        
        Args:
            endpoint: API endpoint identifier
            limits: Rate limits for different time windows
            client_key: Optional client identifier
            
        Returns:
            Tuple of (is_allowed, limit_info)
        """
        client_key = client_key or self._get_client_key()
        
        # Check if client is blocked
        if client_key in self.blocked_ips:
            return False, {
                'error': 'IP blocked',
                'message': 'Your IP has been temporarily blocked due to suspicious activity'
            }
        
        limit_info = {
            'client_key': client_key,
            'endpoint': endpoint,
            'limits': {},
            'current_usage': {},
            'reset_times': {}
        }
        
        for window, limit in limits.items():
            is_allowed, current_count, reset_time = self._check_window_limit(
                client_key, endpoint, window, limit
            )
            
            limit_info['limits'][window] = limit
            limit_info['current_usage'][window] = current_count
            limit_info['reset_times'][window] = reset_time
            
            if not is_allowed:
                # Check for potential DDoS attack
                if current_count > limit * 2:
                    self._handle_potential_attack(client_key, endpoint, current_count, limit)
                
                return False, limit_info
        
        return True, limit_info
    
    def _check_window_limit(self, client_key: str, endpoint: str, window: str, 
                           limit: int) -> Tuple[bool, int, int]:
        """Check rate limit for a specific time window"""
        current_time = int(time.time())
        window_size = RateLimitConfig.TIME_WINDOWS[window]
        window_start = current_time - window_size
        
        rate_key = self._get_rate_limit_key(client_key, endpoint, window)
        
        if self.redis_client:
            return self._redis_check_window(rate_key, window_start, current_time, limit)
        else:
            return self._memory_check_window(rate_key, window_start, current_time, limit)
    
    def _redis_check_window(self, rate_key: str, window_start: int, 
                           current_time: int, limit: int) -> Tuple[bool, int, int]:
        """Check rate limit using Redis"""
        try:
            # Use Redis sorted set to track requests in time window
            pipe = self.redis_client.pipeline()
            
            # Remove old requests outside the window
            pipe.zremrangebyscore(rate_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(rate_key)
            
            # Add current request
            pipe.zadd(rate_key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(rate_key, RateLimitConfig.TIME_WINDOWS['hour'])
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for current request
            
            reset_time = window_start + RateLimitConfig.TIME_WINDOWS['hour']
            
            return current_count <= limit, current_count, reset_time
            
        except Exception as e:
            logger.error(f"❌ Redis rate limit check failed: {e}")
            return True, 0, 0  # Allow on error
    
    def _memory_check_window(self, rate_key: str, window_start: int, 
                            current_time: int, limit: int) -> Tuple[bool, int, int]:
        """Check rate limit using in-memory storage"""
        if rate_key not in self.fallback_storage:
            self.fallback_storage[rate_key] = []
        
        # Remove old requests
        self.fallback_storage[rate_key] = [
            req_time for req_time in self.fallback_storage[rate_key]
            if req_time > window_start
        ]
        
        # Add current request
        self.fallback_storage[rate_key].append(current_time)
        
        current_count = len(self.fallback_storage[rate_key])
        reset_time = window_start + RateLimitConfig.TIME_WINDOWS['hour']
        
        return current_count <= limit, current_count, reset_time
    
    def _handle_potential_attack(self, client_key: str, endpoint: str, 
                               current_count: int, limit: int):
        """Handle potential DDoS attack"""
        logger.warning(f"⚠️  Potential attack detected from {client_key}")
        logger.warning(f"   Endpoint: {endpoint}, Count: {current_count}, Limit: {limit}")
        
        # Temporarily block the IP
        self.blocked_ips.add(client_key)
        
        # Store in Redis with expiration
        if self.redis_client:
            block_key = f"blocked_ip:{client_key}"
            self.redis_client.setex(block_key, 3600, "blocked")  # Block for 1 hour
        
        # Log attack details
        attack_info = {
            'client_key': client_key,
            'endpoint': endpoint,
            'count': current_count,
            'limit': limit,
            'timestamp': datetime.utcnow().isoformat(),
            'user_agent': request.headers.get('User-Agent', ''),
            'ip': request.remote_addr
        }
        
        logger.error(f"🚨 ATTACK BLOCKED: {json.dumps(attack_info)}")
    
    def unblock_ip(self, client_key: str) -> bool:
        """Unblock an IP address"""
        try:
            self.blocked_ips.discard(client_key)
            
            if self.redis_client:
                block_key = f"blocked_ip:{client_key}"
                self.redis_client.delete(block_key)
            
            logger.info(f"✅ Unblocked IP: {client_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to unblock IP {client_key}: {e}")
            return False
    
    def get_rate_limit_stats(self, client_key: str = None) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        client_key = client_key or self._get_client_key()
        
        stats = {
            'client_key': client_key,
            'blocked': client_key in self.blocked_ips,
            'current_limits': {}
        }
        
        # Get current usage for all endpoints
        if self.redis_client:
            try:
                keys = self.redis_client.keys(f"rate_limit:{client_key}:*")
                for key in keys:
                    parts = key.split(':')
                    if len(parts) >= 4:
                        endpoint = parts[2]
                        window = parts[3]
                        count = self.redis_client.zcard(key)
                        
                        if endpoint not in stats['current_limits']:
                            stats['current_limits'][endpoint] = {}
                        
                        stats['current_limits'][endpoint][window] = count
                        
            except Exception as e:
                logger.error(f"❌ Failed to get rate limit stats: {e}")
        
        return stats
    
    def cleanup_expired_limits(self) -> int:
        """Clean up expired rate limit entries"""
        if not self.redis_client:
            return 0
        
        try:
            # Clean up old rate limit keys
            keys = self.redis_client.keys("rate_limit:*")
            cleaned = 0
            
            for key in keys:
                # Check if key has any recent activity
                if self.redis_client.zcard(key) == 0:
                    self.redis_client.delete(key)
                    cleaned += 1
            
            # Clean up blocked IPs
            blocked_keys = self.redis_client.keys("blocked_ip:*")
            for key in blocked_keys:
                if not self.redis_client.exists(key):
                    client_key = key.split(':', 1)[1]
                    self.blocked_ips.discard(client_key)
            
            logger.info(f"✅ Cleaned up {cleaned} expired rate limit entries")
            return cleaned
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up rate limits: {e}")
            return 0


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limits: Dict[str, int] = None, per_user: bool = False):
    """
    Rate limiting decorator
    
    Args:
        limits: Rate limits for different time windows
        per_user: Whether to apply limits per authenticated user
    """
    if limits is None:
        limits = RateLimitConfig.DEFAULT_LIMITS
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get endpoint identifier
            endpoint = request.endpoint or f.__name__
            
            # Get client identifier
            client_key = None
            if per_user:
                # Use authenticated user ID if available
                from auth import get_current_user
                user_id = get_current_user()
                if user_id:
                    client_key = f"user:{user_id}"
            
            # Check rate limit
            is_allowed, limit_info = rate_limiter.check_rate_limit(
                endpoint, limits, client_key
            )
            
            if not is_allowed:
                response_data = {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'limits': limit_info.get('limits', {}),
                    'current_usage': limit_info.get('current_usage', {}),
                    'reset_times': limit_info.get('reset_times', {})
                }
                
                # Add rate limit headers
                response = jsonify(response_data)
                response.status_code = 429
                
                # Add standard rate limit headers
                if 'hour' in limit_info.get('limits', {}):
                    response.headers['X-RateLimit-Limit'] = str(limit_info['limits']['hour'])
                    response.headers['X-RateLimit-Remaining'] = str(
                        max(0, limit_info['limits']['hour'] - limit_info['current_usage']['hour'])
                    )
                    response.headers['X-RateLimit-Reset'] = str(limit_info['reset_times']['hour'])
                
                return response
            
            # Add rate limit info to request context
            g.rate_limit_info = limit_info
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def strict_rate_limit():
    """Decorator for strict rate limiting on sensitive endpoints"""
    return rate_limit(RateLimitConfig.STRICT_LIMITS)


def auth_rate_limit():
    """Decorator for authentication endpoint rate limiting"""
    return rate_limit(RateLimitConfig.AUTH_LIMITS)


def upload_rate_limit():
    """Decorator for file upload rate limiting"""
    return rate_limit(RateLimitConfig.UPLOAD_LIMITS)


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return rate_limiter