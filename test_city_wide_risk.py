"""
Test City-Wide Risk Logic
"""
from mitigation_module.mitigation_solver import solve_guardian_plan, generate_impact_report
from mitigation_module.dynamic_network import reset_dynamic_routes

# Reset to clean state
reset_dynamic_routes()

print("=" * 70)
print("TESTING CITY-WIDE RISK LOGIC")
print("=" * 70)

test_cases = [
    ("Chicago", "Should affect ALL routes (city-wide FAILURE)"),
    ("Mumbai", "Should affect ALL routes (city-wide COLLAPSE)"),
    ("Los Angeles", "Should affect ALL routes (city-wide EARTHQUAKE)"),
]

for city, expected in test_cases:
    print(f"\n{'='*70}")
    print(f"TEST: {city}")
    print(f"Expected: {expected}")
    print("=" * 70)
    
    initial, mitigation, risk_info, destination, requirements = solve_guardian_plan(f"Ship to {city}")
    
    print(f"\nRisk Info: {risk_info}")
    print(f"\nInitial Plan: {initial}")
    print(f"Mitigation Plan: {mitigation}")
    
    # Check if plans are the same (meaning all routes affected)
    if initial == mitigation:
        print("\n⚠️ RESULT: All routes equally expensive - NO REROUTING POSSIBLE")
        print("   Recommendation: Delay shipment or choose alternate destination")
    else:
        print("\n✅ RESULT: Backup route still viable - REROUTING SUCCESSFUL")
    
    report = generate_impact_report(initial, mitigation, destination)
    print(f"\nRoute Impact Table:")
    print(report.to_string(index=False))

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)
