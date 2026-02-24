"""
Test Guardian Mode to verify dynamic rerouting
"""
from mitigation_module.mitigation_solver import solve_guardian_plan

print("=" * 60)
print("TESTING GUARDIAN MODE - DYNAMIC REROUTING")
print("=" * 60)

# Test 1: Ship to Chicago
print("\n\n🧪 TEST 1: Ship to Chicago")
print("-" * 60)
initial, mitigation, risk_info, dest, reqs = solve_guardian_plan("I need to ship 200 units to Chicago on Feb 2")

print(f"\n📊 Risk Info: {risk_info}")
print(f"\n📦 Initial Plan:")
for route_id, qty in sorted(initial.items()):
    if qty > 0:
        print(f"   Route {route_id}: {qty} units")

print(f"\n🛡️ Mitigation Plan:")
for route_id, qty in sorted(mitigation.items()):
    if qty > 0:
        print(f"   Route {route_id}: {qty} units")

# Compare plans
print("\n🔄 Route Changes:")
for route_id in sorted(set(list(initial.keys()) + list(mitigation.keys()))):
    old_qty = initial.get(route_id, 0)
    new_qty = mitigation.get(route_id, 0)
    if old_qty != new_qty:
        print(f"   Route {route_id}: {old_qty} → {new_qty} units")

# Test 2: Ship to Boston
print("\n\n🧪 TEST 2: Ship to Boston")
print("-" * 60)
initial2, mitigation2, risk_info2, dest2, reqs2 = solve_guardian_plan("Ship 100 units to Boston")

print(f"\n📊 Risk Info: {risk_info2}")
print(f"\n📦 Initial Plan:")
for route_id, qty in sorted(initial2.items()):
    if qty > 0:
        print(f"   Route {route_id}: {qty} units")

print(f"\n🛡️ Mitigation Plan:")
for route_id, qty in sorted(mitigation2.items()):
    if qty > 0:
        print(f"   Route {route_id}: {qty} units")

print("\n\n" + "=" * 60)
print("✅ Test Complete!")
print("=" * 60)
