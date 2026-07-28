from typing import Any, Dict, Optional
import time
import json
import os
from .logger import app_logger

class SimpleCache:
    """A simple dictionary-based in-memory cache with TTL."""
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            item = self._cache[key]
            # Check if TTL expired (if TTL is set and > 0)
            if item['expires_at'] and time.time() > item['expires_at']:
                del self._cache[key]
                app_logger.info(
                    "Cache expired",
                    extra={"extra_data": {"cache_key": key, "cache_hit": False}},
                )
                return None
            app_logger.info(
                "Cache hit",
                extra={"extra_data": {"cache_key": key, "cache_hit": True}},
            )
            return item['value']
        app_logger.info(
            "Cache miss",
            extra={"extra_data": {"cache_key": key, "cache_hit": False}},
        )
        return None
        
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._cache[key] = {'value': value, 'expires_at': expires_at}
        app_logger.info(
            "Cache set",
            extra={"extra_data": {"cache_key": key, "ttl_seconds": ttl_seconds}},
        )
        
    def clear(self):
        self._cache.clear()

# Global cache instance
app_cache = SimpleCache()

def save_to_disk(data: Any, filepath: str):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f)
        app_logger.info(f"Successfully saved data to disk at {filepath}")
    except Exception as e:
        app_logger.error(f"Optimization persistence failed | exception={str(e)}")

def load_from_disk(filepath: str) -> Optional[Any]:
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        app_logger.info(f"Successfully loaded data from disk at {filepath}")
        return data
    except Exception as e:
        app_logger.error(f"Failed to load data from disk | exception={str(e)}")
        return None
