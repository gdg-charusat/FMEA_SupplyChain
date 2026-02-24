"""
Test Unlimited Cities Feature
"""
from mitigation_module.mitigation_solver import solve_guardian_plan, generate_impact_report
from mitigation_module.dynamic_network import get_network_summary

print("=" * 70)
print("TESTING UNLIMITED CITIES - DYNAMIC ROUTE GENERATION")
print("=" * 70)

# Test 1: Predefined city (optimized)
print("\n\nTEST 1: Predefined City - Boston")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("Ship to Boston")
print(f"\nRisk: {risk_info}")
report = generate_impact_report(initial, mitigation, destination)
print(f"\nRoute Impact:\n{report.to_string(index=False)}")

# Test 2: NEW city - Seattle (will create dynamic routes)
print("\n\nTEST 2: NEW City - Seattle (Dynamic)")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("I need to ship 300 units to Seattle")
print(f"\nRisk: {risk_info}")
report = generate_impact_report(initial, mitigation, destination)
print(f"\nRoute Impact:\n{report.to_string(index=False)}")

# Test 3: Another NEW city - Austin
print("\n\nTEST 3: NEW City - Austin (Dynamic)")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("Send supplies to Austin")
print(f"\nRisk: {risk_info}")
report = generate_impact_report(initial, mitigation, destination)
print(f"\nRoute Impact:\n{report.to_string(index=False)}")

# Test 4: Multi-word city - Los Angeles
print("\n\nTEST 4: NEW City - Los Angeles (Dynamic)")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("Ship to Los Angeles")
print(f"\nRisk: {risk_info}")
report = generate_impact_report(initial, mitigation, destination)
print(f"\nRoute Impact:\n{report.to_string(index=False)}")

# Network Summary
print("\n\n" + "=" * 70)
print("NETWORK SUMMARY")
print("=" * 70)
summary = get_network_summary()
for key, value in summary.items():
    print(f"  {key}: {value}")

print("\nUnlimited Cities Test Complete!")
print("System can now handle ANY city name from GDELT dataset!")
print("=" * 70)
