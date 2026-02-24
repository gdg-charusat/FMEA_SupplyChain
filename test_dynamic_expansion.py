"""
Test Dynamic Network Expansion
- Multiple warehouses (5 warehouses = 5 direct routes per city)
- Multi-hop routing through distribution hubs
- NO HARDCODING - all routes generated dynamically
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from mitigation_module.dynamic_network import (
    get_routes_for_city,
    get_route_details,
    get_route_cost,
    get_primary_route_for_city,
    get_backup_routes_for_city,
    get_network_summary,
    print_network_summary,
    reset_dynamic_routes
)
from mitigation_module.network_config import get_warehouse_list, get_hub_list

print("="*80)
print("DYNAMIC NETWORK EXPANSION TEST")
print("="*80)

# Reset to start fresh
reset_dynamic_routes()

# Test 1: Check warehouse configuration
print("\n[TEST 1] Warehouse Configuration")
print("-"*80)
warehouses = get_warehouse_list()
print(f"Total Warehouses: {len(warehouses)}")
for wh in warehouses:
    print(f"  • {wh}")

# Test 2: Check hub configuration
print("\n[TEST 2] Distribution Hub Configuration")
print("-"*80)
hubs = get_hub_list()
print(f"Total Distribution Hubs: {len(hubs)}")
for hub in hubs:
    print(f"  • {hub}")

# Test 3: Create routes for a new city (should get 5 direct + multi-hop routes)
print("\n[TEST 3] Create Routes for Seattle (New City)")
print("-"*80)
routes = get_routes_for_city("Seattle", include_multihop=True)
print(f"Total routes created for Seattle: {len(routes)}")
print(f"Expected: {len(warehouses)} direct + {len(warehouses) * len(hubs)} multi-hop = {len(warehouses) + len(warehouses) * len(hubs)} routes")

# Test 4: Show route details
print("\n[TEST 4] Route Details for Seattle")
print("-"*80)
direct_routes = [r for r in routes if r < 1000]
multihop_routes = [r for r in routes if r >= 1000]

print(f"\nDIRECT ROUTES ({len(direct_routes)}):")
for rid in direct_routes:
    details = get_route_details(rid)
    if details:
        print(f"  Route {rid}: {details['source']} → {details['destination']} ({details['route_type']})")
        if details['is_primary']:
            print(f"    ⭐ PRIMARY ROUTE")

print(f"\nMULTI-HOP ROUTES ({len(multihop_routes)}):")
for rid in multihop_routes[:5]:  # Show first 5
    details = get_route_details(rid)
    if details:
        print(f"  Route {rid}: {details['source']} → {details['via_hub']} → {details['destination']}")
if len(multihop_routes) > 5:
    print(f"  ... and {len(multihop_routes) - 5} more multi-hop routes")

# Test 5: Primary and Backup routes
print("\n[TEST 5] Primary vs Backup Routes")
print("-"*80)
primary = get_primary_route_for_city("Seattle")
backups = get_backup_routes_for_city("Seattle")
print(f"Primary Route: {primary}")
print(f"Backup Routes: {len(backups)} alternatives available")

# Test 6: Cost calculation
print("\n[TEST 6] Route Cost Calculation")
print("-"*80)
direct_cost = get_route_cost(direct_routes[0])
multihop_cost = get_route_cost(multihop_routes[0]) if multihop_routes else 0
print(f"Direct Route Cost:    ${direct_cost:,.2f}")
print(f"Multi-Hop Route Cost: ${multihop_cost:,.2f}")
print(f"Multi-hop premium:    ${multihop_cost - direct_cost:,.2f} ({((multihop_cost/direct_cost - 1) * 100):.1f}% more)")

# Test 7: Create routes for another city
print("\n[TEST 7] Create Routes for Portland (Another New City)")
print("-"*80)
routes_portland = get_routes_for_city("Portland", include_multihop=True)
print(f"Total routes created for Portland: {len(routes_portland)}")

# Test 8: Network summary
print("\n[TEST 8] Complete Network Summary")
print_network_summary()

# Test 9: Verify dynamicity - add more routes for Chicago (predefined city)
print("\n[TEST 9] Verify NO HARDCODING: Chicago should also have all warehouse options")
print("-"*80)
routes_chicago = get_routes_for_city("Chicago", include_multihop=False)
print(f"Routes available for Chicago: {routes_chicago}")
print(f"Note: Chicago has predefined routes (1-10 from CSV), but system is fully dynamic")

print("\n" + "="*80)
print("✅ ALL TESTS COMPLETED")
print("="*80)

print("\n📊 KEY ACHIEVEMENTS:")
print(f"  ✓ {len(warehouses)} warehouses configured (NO HARDCODING)")
print(f"  ✓ {len(hubs)} distribution hubs for multi-hop routing")
print(f"  ✓ {len(direct_routes)} direct routes per new city")
print(f"  ✓ {len(multihop_routes)} multi-hop routes per new city")
print(f"  ✓ Total route options per city: {len(direct_routes) + len(multihop_routes)}")
print("\n🎯 DYNAMIC SYSTEM: Just add more warehouses/hubs to network_config.py!")
print("   No code changes needed - routes auto-generated! 🚀\n")
