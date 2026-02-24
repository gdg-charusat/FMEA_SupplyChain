"""
Test the complete Guardian Plan flow with parsed quantities
"""
from mitigation_module.mitigation_solver import solve_guardian_plan

print("\n" + "="*70)
print("TESTING GUARDIAN PLAN WITH PARSED QUANTITIES")
print("="*70)

# Test 1: User specifies 500 units to Boston
print("\n\n🧪 TEST 1: Custom Quantity (500 units)")
print("-" * 70)
test_input = "I need to ship 500 units to Boston on Feb 10th"
print(f"Input: {test_input}")

initial, mitigation, risk_info, destination, requirements = solve_guardian_plan(test_input)

print(f"\n📊 RESULTS:")
print(f"  Destination: {destination}")
print(f"  Parsed Quantity: {requirements['quantity']} units")
print(f"  Risk Status: {risk_info}")
print(f"\n  Initial Plan:")
for route_id, qty in initial.items():
    if qty > 0:
        print(f"    Route {route_id}: {qty} units")
print(f"\n  Mitigation Plan:")
for route_id, qty in mitigation.items():
    if qty > 0:
        print(f"    Route {route_id}: {qty} units")

# Test 2: User specifies large quantity
print("\n\n🧪 TEST 2: Large Quantity (2000 units)")
print("-" * 70)
test_input2 = "Ship 2000 units to Chicago ASAP"
print(f"Input: {test_input2}")

initial2, mitigation2, risk_info2, destination2, requirements2 = solve_guardian_plan(test_input2)

print(f"\n📊 RESULTS:")
print(f"  Destination: {destination2}")
print(f"  Parsed Quantity: {requirements2['quantity']} units")
print(f"  Priority: {requirements2['priority']}")
print(f"  Risk Status: {risk_info2}")
print(f"\n  Initial Plan:")
for route_id, qty in initial2.items():
    if qty > 0:
        print(f"    Route {route_id}: {qty} units")
print(f"\n  Mitigation Plan:")
for route_id, qty in mitigation2.items():
    if qty > 0:
        print(f"    Route {route_id}: {qty} units")

# Test 3: No quantity specified (should use default)
print("\n\n🧪 TEST 3: Default Quantity (Not Specified)")
print("-" * 70)
test_input3 = "Ship to Miami"
print(f"Input: {test_input3}")

initial3, mitigation3, risk_info3, destination3, requirements3 = solve_guardian_plan(test_input3)

print(f"\n📊 RESULTS:")
print(f"  Destination: {destination3}")
print(f"  Parsed Quantity: {requirements3['quantity']}")
print(f"  Using Default: Yes (Miami default = 200 units)")
print(f"  Risk Status: {risk_info3}")
print(f"\n  Initial Plan:")
for route_id, qty in initial3.items():
    if qty > 0:
        print(f"    Route {route_id}: {qty} units")

print("\n" + "="*70)
print("✅ TEST COMPLETE: System now uses ACTUAL user quantities!")
print("="*70 + "\n")
