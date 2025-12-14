"""
Enhanced Caching System
Multi-level caching with TTL, LRU eviction, and cache warming
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from collections import OrderedDict
from threading import RLock
import hashlib
import json
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheEntry:
    """Individual cache entry with metadata"""
    
    def __init__(self, key: str, value: Any, ttl: int):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return datetime.now() >= self.expires_at
    
    def access(self) -> Any:
        """Access entry and update metadata"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value
    
    def remaining_ttl(self) -> int:
        """Get remaining TTL in seconds"""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))


class LRUCache:
    """Thread-safe LRU cache with TTL"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                self._misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self._hits += 1
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self.lock:
            ttl = ttl or self.default_ttl
            
            # Remove if exists (to update position)
            if key in self.cache:
                del self.cache[key]
            
            # Evict oldest if at capacity
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")
            
            # Add new entry
            self.cache[key] = CacheEntry(key, value, ttl)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Deleted cache entry: {key}")
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries
        
        Returns:
            Number of entries removed
        """
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests
            }


class PredictionCache:
    """Specialized cache for NHL predictions"""
    
    def __init__(self, ttl_hours: int = 6, max_size: int = 500):
        """
        Args:
            ttl_hours: Cache TTL in hours
            max_size: Maximum cache entries
        """
        self.cache = LRUCache(max_size=max_size, default_ttl=ttl_hours * 3600)
    
    def _generate_key(self, home_team: str, away_team: str, game_date: str) -> str:
        """Generate cache key from game details"""
        data = f"{home_team}_{away_team}_{game_date}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get_prediction(self, home_team: str, away_team: str, game_date: str) -> Optional[Dict]:
        """Get cached prediction"""
        key = self._generate_key(home_team, away_team, game_date)
        return self.cache.get(key)
    
    def set_prediction(self, home_team: str, away_team: str, game_date: str, prediction: Dict):
        """Cache prediction"""
        key = self._generate_key(home_team, away_team, game_date)
        self.cache.set(key, prediction)
    
    def invalidate_prediction(self, home_team: str, away_team: str, game_date: str) -> bool:
        """Invalidate cached prediction"""
        key = self._generate_key(home_team, away_team, game_date)
        return self.cache.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


class FilesystemCache:
    """Filesystem-based cache for persistence"""
    
    def __init__(self, cache_dir: str = "./cache", ttl: int = 86400):
        """
        Args:
            cache_dir: Directory for cache files
            ttl: Time-to-live in seconds (default 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
    
    def _get_path(self, key: str) -> Path:
        """Get cache file path for key"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from filesystem cache"""
        path = self._get_path(key)
        
        if not path.exists():
            return None
        
        try:
            # Check if expired
            file_age = datetime.now().timestamp() - path.stat().st_mtime
            if file_age > self.ttl:
                path.unlink()
                return None
            
            # Load from file
            with open(path, "rb") as f:
                return pickle.load(f)
        
        except Exception as e:
            logger.error(f"Error loading from filesystem cache: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Set value in filesystem cache"""
        path = self._get_path(key)
        
        try:
            with open(path, "wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.error(f"Error writing to filesystem cache: {e}")
    
    def delete(self, key: str):
        """Delete value from filesystem cache"""
        path = self._get_path(key)
        if path.exists():
            path.unlink()
    
    def clear(self):
        """Clear all filesystem cache"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        logger.info("Filesystem cache cleared")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache files"""
        count = 0
        now = datetime.now().timestamp()
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                file_age = now - cache_file.stat().st_mtime
                if file_age > self.ttl:
                    cache_file.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Error cleaning up {cache_file}: {e}")
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired filesystem cache entries")
        
        return count


def cached(cache: LRUCache, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        cache: Cache instance to use
        ttl: Time-to-live override
        key_func: Custom function to generate cache key from args
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and arguments
                key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator
