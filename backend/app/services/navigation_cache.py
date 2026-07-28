import time
from typing import Dict, Any, Optional

class NavigationCache:
    def __init__(self, ttl_seconds: int = 900): # 15 minutes
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def _generate_key(self, origin: str, destination: str) -> str:
        return f"{origin}_{destination}"

    def get(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        key = self._generate_key(origin, destination)
        entry = self.cache.get(key)
        
        if entry:
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["data"]
            else:
                del self.cache[key]
        return None

    def set(self, origin: str, destination: str, data: Dict[str, Any]) -> None:
        key = self._generate_key(origin, destination)
        self.cache[key] = {
            "timestamp": time.time(),
            "data": data
        }

navigation_cache = NavigationCache()
