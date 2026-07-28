"""
Clear the route cache to ensure fresh results after fixes.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.routing_service import route_cache, hub_cache

print("=" * 80)
print("CLEARING ROUTE CACHE")
print("=" * 80)

print(f"\nRoute cache size before: {len(route_cache)}")
print(f"Hub cache size before: {len(hub_cache)}")

# Clear caches
route_cache.clear()
hub_cache.clear()

print(f"\nRoute cache size after: {len(route_cache)}")
print(f"Hub cache size after: {len(hub_cache)}")

print("\n✅ Caches cleared successfully")
