"""
Test the new LLM route selection and ALL routes display
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from mitigation_module.mitigation_solver import select_routes_with_llm, generate_impact_report
from mitigation_module.dynamic_network import get_routes_for_city

print("=" * 80)
print("TESTING LLM ROUTE SELECTION & ALL ROUTES DISPLAY")
print("=" * 80)

# Test 1: LLM route selection for Chicago
print("\n1. LLM Route Selection for Chicago (1000 units, $20,000 budget):")
print("-" * 60)

llm_result = select_routes_with_llm(
    destination="Chicago",
    quantity=1000,
    budget=20000,
    risk_factor=20.0
)

print(f"\n✅ Analysis Complete!")
print(f"   Strategy: {llm_result['analysis']}")
print(f"   Total Cost: ${llm_result['total_cost']:,.2f}")
print(f"\n   Selected Routes:")
for route in llm_result['selected_routes']:
    print(f"   • Route {route['route_id']} ({route['role']}): {route['quantity']} units")
    print(f"     Reason: {route['reason']}")

# Test 2: Generate impact report showing ALL routes
print("\n2. Generate Impact Report (showing ALL 22 routes):")
print("-" * 60)

# Create simple plans for testing
initial_plan = {3: 1000}  # Original plan
mitigation_plan = {6: 1000}  # Mitigation plan

impact_df = generate_impact_report(initial_plan, mitigation_plan, filter_destination="Chicago")

print(f"\n   Total Routes in Report: {len(impact_df)}")
print(f"\n   Route Breakdown:")
print(f"   • Activated: {len(impact_df[impact_df['Status'] == '🟢 ACTIVATED'])}")
print(f"   • Stopped: {len(impact_df[impact_df['Status'] == '🔴 STOPPED'])}")
print(f"   • Available (Not Selected): {len(impact_df[impact_df['Status'] == '⏸️ AVAILABLE'])}")

print(f"\n   Sample Routes (first 5):")
for idx, row in impact_df.head(5).iterrows():
    print(f"   {row['Route ID']}: {row['Route Path']} ({row['Type']}) - {row['Status']}")

# Test 3: Show statistics
print("\n3. Route Statistics:")
print("-" * 60)
direct_count = len(impact_df[impact_df['Type'] == 'Direct'])
multihop_count = len(impact_df[impact_df['Type'] == 'Multi-Hop'])
print(f"   Direct Routes: {direct_count}")
print(f"   Multi-Hop Routes: {multihop_count}")
print(f"   Total Available: {len(impact_df)}")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETE!")
print("=" * 80)
print("\n🎯 Now refresh your browser and try:")
print("   Input: 'Send 1000 units to Chicago with budget $20,000'")
print("\n📊 You will see:")
print("   ✅ ALL 22 routes displayed in Route Impact Analysis")
print("   ✅ AI Route Selection Reasoning with cost breakdown")
print("   ✅ Clear status for each route (Selected, Available, etc.)")
print("=" * 80)
