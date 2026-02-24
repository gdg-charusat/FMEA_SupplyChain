"""
Test script for the narrative-driven report generator
Demonstrates output with the JFK Airport/Port of New York scenario
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from mitigation_module import (
    TransportOptimizer,
    DisruptionExtractor,
    generate_impact_report,
    ROUTE_MAP
)

def main():
    print("\n" + "="*70)
    print("  SUPPLY CHAIN RISK MITIGATION - NARRATIVE REPORT DEMO")
    print("="*70 + "\n")
    
    # The logistics alert from your example
    logistics_alert = """
OFFICIAL LOGISTICS ALERT
From: Global Freight Authority
Date: 2026-02-03
Severity: CRITICAL

Subject: Port of New York (Route 2) & Philadelphia Access Suspended

Details: Due to an ongoing labor strike at the JFK Airport cargo terminal and 
the adjacent Port of New York, all inbound shipments are currently blocked.

Impact Assessment:
- Affected Routes: New York Inbound (Route 2) and Philadelphia Corridor (Route 5).
- Cost Implication: Emergency air freight alternatives are required. 
  Expect transport costs to increase by 500% (5.0x multiplier).
- Duration: Indefinite.

Action Required: Reroute all "Fresh" and "Refrigerated" category goods 
immediately to the secondary warehouse.
"""
    
    print("📋 INPUT ALERT:")
    print("-" * 70)
    print(logistics_alert)
    print("-" * 70 + "\n")
    
    # Step 1: Extract disruptions
    print("🔍 STEP 1: Extracting disruption information...")
    extractor = DisruptionExtractor()
    events = extractor.extract_from_text(logistics_alert)
    disruptions = [e.to_dict() for e in events]
    
    print(f"✅ Extracted {len(disruptions)} disruption event(s):\n")
    for i, d in enumerate(disruptions, 1):
        print(f"  {i}. Route {d['target_route_id']}: {d['impact_type']} "
              f"(×{d['cost_multiplier']}, severity: {d['severity_score']}/10)")
    
    print("\n" + "="*70 + "\n")
    
    # Step 2: Run optimization
    print("🚀 STEP 2: Running Linear Programming optimization...")
    optimizer = TransportOptimizer()
    
    # Get baseline (no disruptions)
    print("   - Calculating baseline plan...")
    baseline = optimizer.solve(use_disrupted_costs=False)
    
    if baseline['status'] != 'success':
        print("❌ Baseline optimization failed!")
        return
    
    print(f"   ✓ Baseline cost: ${baseline['total_cost']:,.2f}")
    
    # Apply disruptions
    optimizer.apply_disruptions(disruptions)
    
    # Get adjusted plan
    print("   - Calculating risk-adjusted plan...")
    adjusted = optimizer.solve(use_disrupted_costs=True)
    
    if adjusted['status'] != 'success':
        print("❌ Adjusted optimization failed!")
        return
    
    print(f"   ✓ Adjusted cost: ${adjusted['total_cost']:,.2f}")
    print(f"   ✓ Cost increase: ${adjusted['total_cost'] - baseline['total_cost']:,.2f}\n")
    
    print("="*70 + "\n")
    
    # Step 3: Generate narrative report
    print("📊 STEP 3: Generating narrative-driven impact report...\n")
    
    summary_text, impact_table, cost_delta_pct = generate_impact_report(
        initial_solution=baseline,
        new_solution=adjusted,
        route_map=ROUTE_MAP,
        disruptions=disruptions
    )
    
    # Display narrative
    print("🎯 STRATEGIC NARRATIVE:")
    print("-" * 70)
    print(summary_text)
    print("-" * 70 + "\n")
    
    # Display impact table
    print("📋 ROUTE IMPACT ANALYSIS:")
    print("-" * 70)
    
    if not impact_table.empty:
        # Print table with nice formatting
        print(impact_table.to_string(index=False))
    else:
        print("No route changes detected")
    
    print("-" * 70 + "\n")
    
    # Display summary metrics
    print("💰 COST ANALYSIS:")
    print("-" * 70)
    print(f"Original Plan Cost:      ${baseline['total_cost']:>15,.2f}")
    print(f"Risk-Adjusted Cost:      ${adjusted['total_cost']:>15,.2f}")
    print(f"Cost Increase:           ${adjusted['total_cost'] - baseline['total_cost']:>15,.2f}")
    print(f"Percentage Increase:     {cost_delta_pct:>15.1f}%")
    print("-" * 70 + "\n")
    
    # Display flow details
    print("📦 DETAILED FLOW CHANGES:")
    print("-" * 70)
    
    for route_id in sorted(ROUTE_MAP.keys()):
        old_flow = baseline['flows'].get(route_id, 0)
        new_flow = adjusted['flows'].get(route_id, 0)
        
        if old_flow > 0 or new_flow > 0:
            source, dest = ROUTE_MAP[route_id]
            dest_clean = dest.replace("Client_", "")
            
            if abs(old_flow - new_flow) > 0.01:
                change = new_flow - old_flow
                status = ""
                if old_flow > 0 and new_flow == 0:
                    status = "🔴 STOPPED"
                elif old_flow == 0 and new_flow > 0:
                    status = "🟢 ACTIVATED"
                elif old_flow > 0 and new_flow > 0:
                    status = "🟡 BALANCED"
                
                print(f"Route {route_id:2d} to {dest_clean:15s}: "
                      f"{old_flow:6.0f} → {new_flow:6.0f} units "
                      f"({change:+7.0f}) {status}")
    
    print("-" * 70 + "\n")
    
    print("✅ REPORT GENERATION COMPLETE!\n")
    print("="*70)
    print("\n💡 Next Steps:")
    print("   1. Run Streamlit dashboard: streamlit run app.py")
    print("   2. Navigate to 🚚 Supply Chain Risk tab")
    print("   3. Paste the alert text and click 'Analyze Disruption'")
    print("   4. View the narrative-driven visualization\n")


if __name__ == "__main__":
    main()
