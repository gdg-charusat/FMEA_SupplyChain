"""
Quick test to verify dynamic routes are created for ALL cities
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from mitigation_module.dynamic_network import get_routes_for_city, get_full_route_map

print("=" * 80)
print("TESTING DYNAMIC ROUTE GENERATION FIX")
print("=" * 80)

# Test 1: Chicago (has predefined routes)
print("\n1. Testing CHICAGO (has predefined routes 1 & 6):")
print("-" * 60)
chicago_routes = get_routes_for_city("Chicago", include_multihop=True)
print(f"   Total routes for Chicago: {len(chicago_routes)}")
print(f"   Route IDs: {chicago_routes}")

# Test 2: Boston (has predefined routes)
print("\n2. Testing BOSTON (has predefined route 1):")
print("-" * 60)
boston_routes = get_routes_for_city("Boston", include_multihop=True)
print(f"   Total routes for Boston: {len(boston_routes)}")
print(f"   Route IDs: {boston_routes}")

# Test 3: New city (no predefined routes)
print("\n3. Testing SEATTLE (no predefined routes):")
print("-" * 60)
seattle_routes = get_routes_for_city("Seattle", include_multihop=True)
print(f"   Total routes for Seattle: {len(seattle_routes)}")
print(f"   Route IDs: {seattle_routes}")

# Test 4: Check full route map
print("\n4. Full Route Map Summary:")
print("-" * 60)
full_map = get_full_route_map()
print(f"   Total routes in system: {len(full_map)}")

# Count route types
direct_count = sum(1 for r in full_map.values() if len(r) == 2)
multihop_count = sum(1 for r in full_map.values() if len(r) == 3)
print(f"   Direct routes: {direct_count}")
print(f"   Multi-hop routes: {multihop_count}")

# Show sample routes for Chicago
print("\n5. Sample Routes for Chicago:")
print("-" * 60)
for route_id in sorted(chicago_routes[:10]):  # Show first 10
    if route_id in full_map:
        route_tuple = full_map[route_id]
        if len(route_tuple) == 2:
            src, dst = route_tuple
            print(f"   Route {route_id}: {src} → {dst} (Direct)")
        else:
            src, hub, dst = route_tuple
            print(f"   Route {route_id}: {src} → {hub} → {dst} (Multi-Hop)")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE!")
print("=" * 80)
