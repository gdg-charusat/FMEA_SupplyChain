"""
Test scenario: Disrupt primary route to see backup activation
"""
from mitigation_module import TransportOptimizer, generate_impact_report, ROUTE_MAP

print("=" * 70)
print("Scenario: Route 1 (Primary to Boston) BLOCKED")
print("=" * 70)

# Baseline
optimizer = TransportOptimizer()
baseline = optimizer.solve(use_disrupted_costs=False)

print("\n📋 Baseline Plan:")
for route_id, qty in baseline['flows'].items():
    if qty > 0:
        src, dst = ROUTE_MAP[route_id]
        print(f"  Route {route_id}: {src} → {dst}: {qty} units")

# Apply SEVERE disruption to Route 1 (Primary to Boston)
print("\n⚠️  Applying disruption: Route 1 cost increased 100x (effectively blocked)")
disruptions = [{"target_route_id": 1, "cost_multiplier": 100.0, "severity_score": 10}]
optimizer.apply_disruptions(disruptions)
adjusted = optimizer.solve(use_disrupted_costs=True)

print("\n📋 Adjusted Plan:")
for route_id, qty in adjusted['flows'].items():
    if qty > 0:
        src, dst = ROUTE_MAP[route_id]
        print(f"  Route {route_id}: {src} → {dst}: {qty} units")

# Generate report
print("\n" + "=" * 70)
print("📊 Impact Report")
print("=" * 70 + "\n")

impact_table = generate_impact_report(
    original_flows=baseline['flows'],
    new_flows=adjusted['flows'],
    route_map_data=ROUTE_MAP
)

print(impact_table.to_string(index=False))

print("\n" + "=" * 70)
print("Cost Comparison")
print("=" * 70)
print(f"Baseline cost: ${baseline['total_cost']:,.2f}")
print(f"Adjusted cost: ${adjusted['total_cost']:,.2f}")
cost_delta = adjusted['total_cost'] - baseline['total_cost']
cost_pct = (cost_delta / baseline['total_cost']) * 100
print(f"Cost impact: ${cost_delta:,.2f} (+{cost_pct:.1f}%)")
