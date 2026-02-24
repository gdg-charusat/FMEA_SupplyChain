"""
Test Route-Specific vs City-Wide Risks
"""
from mitigation_module.mitigation_solver import solve_guardian_plan, generate_impact_report
from mitigation_module.dynamic_network import reset_dynamic_routes

reset_dynamic_routes()

print("=" * 70)
print("COMPARISON: ROUTE-SPECIFIC vs CITY-WIDE RISKS")
print("=" * 70)

# Test 1: Route-specific (traffic/delay) - only affects primary route
print("\n1. ROUTE-SPECIFIC RISK: Chennai (TRAFFIC - 2.0x)")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("Ship to Chennai")
print(f"Risk: {risk_info}")
if initial != mitigation:
    print("✅ REROUTING POSSIBLE: Backup route available")
else:
    print("⚠️ NO REROUTING: All routes affected equally")
report = generate_impact_report(initial, mitigation, destination)
print(f"\n{report.to_string(index=False)}")

# Test 2: City-wide (collapse) - affects ALL routes  
print("\n\n2. CITY-WIDE RISK: Mumbai (COLLAPSE - 20.0x)")
print("-" * 70)
initial, mitigation, risk_info, destination, requirements = solve_guardian_plan("Ship to Mumbai")
print(f"Risk: {risk_info}")
if initial != mitigation:
    print("✅ REROUTING POSSIBLE: Backup route available")
else:
    print("⚠️ NO REROUTING: All routes affected equally")
report = generate_impact_report(initial, mitigation, destination)
print(f"\n{report.to_string(index=False)}")

print("\n" + "=" * 70)
print("EXPLANATION:")
print("=" * 70)
print("ROUTE-SPECIFIC (traffic, delay):")
print("  - Only affects PRIMARY route (e.g., highway congestion)")
print("  - Backup route via different path is still viable")
print("  - System can reroute successfully")
print()
print("CITY-WIDE (earthquake, flood, collapse, strike):")
print("  - Affects ALL routes to that destination")
print("  - No backup route can avoid the disaster")
print("  - System recommends DELAYING shipment or alternate city")
print("=" * 70)
