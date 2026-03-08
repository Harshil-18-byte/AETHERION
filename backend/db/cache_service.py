from cachetools import TTLCache, cached
from typing import Any, Callable
import functools

# Global cache for heavy analytics calls
# maxsize=100 items, expires after 300 seconds (5 minutes)
analytics_cache = TTLCache(maxsize=100, ttl=300)

def cache_result(ttl: int = 300):
    """
    Decorator for caching function results with a specific TTL.
    """
    def decorator(func: Callable):
        cache = TTLCache(maxsize=100, ttl=ttl)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from arguments
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator

# Specific cache for the full options chain
options_chain_cache = TTLCache(maxsize=50, ttl=60) # 1 minute for live-ish data
