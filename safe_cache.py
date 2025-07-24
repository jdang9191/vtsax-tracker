"""
Safe Cache System with Fallback
Protects against exceeding Upstash Redis free tier limits
"""

import os
import json
import time
import pickle
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib

class SafeCache:
    """Cache system that respects free tier limits"""
    
    def __init__(self, redis_url=None, daily_limit=9000):
        self.daily_limit = daily_limit  # Stay under 10K Upstash limit
        self.memory_cache = {}  # In-memory fallback
        self.redis_client = None
        self.redis_available = False
        self.request_count = 0
        self.last_reset = datetime.now()
        
        # Try to connect to Redis if URL provided
        if redis_url or os.getenv('UPSTASH_REDIS_URL'):
            try:
                import redis
                self.redis_client = redis.from_url(
                    redis_url or os.getenv('UPSTASH_REDIS_URL'),
                    decode_responses=True
                )
                self.redis_client.ping()
                self.redis_available = True
                print("Connected to Upstash Redis")
            except Exception as e:
                print(f"Redis connection failed, using memory cache: {e}")
                self.redis_available = False
    
    def _check_daily_reset(self):
        """Reset counter if new day"""
        if datetime.now().date() != self.last_reset.date():
            self.request_count = 0
            self.last_reset = datetime.now()
    
    def _under_limit(self):
        """Check if we're under daily limit"""
        self._check_daily_reset()
        return self.request_count < self.daily_limit
    
    def _increment_count(self):
        """Increment request counter"""
        self.request_count += 1
    
    def get(self, key, default=None):
        """Get value from cache with fallback"""
        # Always check memory cache first (free)
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                del self.memory_cache[key]
        
        # Try Redis if available and under limit
        if self.redis_available and self._under_limit():
            try:
                value = self.redis_client.get(key)
                self._increment_count()
                
                if value:
                    # Cache in memory too
                    try:
                        decoded_value = json.loads(value)
                        self._set_memory_cache(key, decoded_value, 300)
                        return decoded_value
                    except:
                        return value
            except Exception as e:
                print(f"Redis get error: {e}")
        
        return default
    
    def set(self, key, value, ttl=300):
        """Set value in cache with TTL"""
        # Always set in memory cache
        self._set_memory_cache(key, value, ttl)
        
        # Try Redis if available and under limit
        if self.redis_available and self._under_limit():
            try:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                self.redis_client.setex(key, ttl, value)
                self._increment_count()
            except Exception as e:
                print(f"Redis set error: {e}")
    
    def _set_memory_cache(self, key, value, ttl):
        """Set value in memory cache"""
        self.memory_cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        
        # Clean up expired entries if cache gets too large
        if len(self.memory_cache) > 1000:
            self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.memory_cache.items() 
            if v['expires'] < current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    def delete(self, key):
        """Delete key from cache"""
        # Delete from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Try Redis if available
        if self.redis_available and self._under_limit():
            try:
                self.redis_client.delete(key)
                self._increment_count()
            except:
                pass
    
    def get_usage_stats(self):
        """Get cache usage statistics"""
        self._check_daily_reset()
        return {
            'redis_available': self.redis_available,
            'daily_requests': self.request_count,
            'daily_limit': self.daily_limit,
            'usage_percentage': (self.request_count / self.daily_limit * 100),
            'memory_cache_size': len(self.memory_cache),
            'using_fallback': not self.redis_available or self.request_count >= self.daily_limit
        }
    
    def cache_decorator(self, ttl=300, key_prefix=''):
        """Decorator for caching function results"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(
                    key_prefix or func.__name__, 
                    args, 
                    kwargs
                )
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    def _generate_cache_key(self, prefix, args, kwargs):
        """Generate a cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()


# Global cache instance
cache = SafeCache()


class CacheFallback:
    """Static file fallback when all caching fails"""
    
    def __init__(self, static_dir='static/cache'):
        self.static_dir = static_dir
        os.makedirs(static_dir, exist_ok=True)
    
    def save_static(self, key, data):
        """Save data as static JSON file"""
        filename = os.path.join(self.static_dir, f"{key}.json")
        try:
            with open(filename, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            print(f"Failed to save static cache: {e}")
            return False
    
    def load_static(self, key):
        """Load data from static JSON file"""
        filename = os.path.join(self.static_dir, f"{key}.json")
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def save_all_holdings(self, holdings_data):
        """Pre-generate static files for all holdings"""
        # Save complete holdings list
        self.save_static('all_holdings', holdings_data)
        
        # Save top 100 holdings
        top_100 = sorted(
            holdings_data, 
            key=lambda x: x.get('percentage', 0), 
            reverse=True
        )[:100]
        self.save_static('top_100_holdings', top_100)
        
        # Save by ticker index for fast lookup
        ticker_index = {h['ticker']: h for h in holdings_data}
        self.save_static('ticker_index', ticker_index)
        
        print(f"Generated {len(holdings_data)} static cache files")


# Example usage with fallback
def get_with_fallback(key, fetch_function, ttl=300):
    """Get data with multiple fallback levels"""
    # Try cache first
    result = cache.get(key)
    if result:
        return result, 'cache'
    
    # Try static fallback
    static_fallback = CacheFallback()
    static_result = static_fallback.load_static(key)
    if static_result:
        return static_result, 'static'
    
    # Fetch fresh data
    try:
        fresh_data = fetch_function()
        cache.set(key, fresh_data, ttl)
        static_fallback.save_static(key, fresh_data)
        return fresh_data, 'fresh'
    except Exception as e:
        print(f"Failed to fetch fresh data: {e}")
        return None, 'error'