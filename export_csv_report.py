"""
Export narrative report to CSV format matching the user's exact specification
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent))

from mitigation_module import (
    TransportOptimizer,
    DisruptionExtractor,
    generate_impact_report,
    ROUTE_MAP
)

def export_to_csv_format(baseline, adjusted, disruptions, route_map, output_path="mitigation_report.csv"):
    """
    Export report in the exact CSV format requested:
    Route Strategy, Original Plan (Standard), New Mitigation Plan (Post-Alert), Status
    """
    
    initial_flows = baseline['flows']
    new_flows = adjusted['flows']
    
    # Get disrupted route IDs
    disrupted_route_ids = [d.get('target_route_id') for d in disruptions]
    
    rows = []
    
    # Get all unique destinations
    destinations = {}
    all_routes = set(list(initial_flows.keys()) + list(new_flows.keys()))
    
    for route_id in all_routes:
        if route_id in route_map:
            source, dest = route_map[route_id]
            if dest not in destinations:
                destinations[dest] = []
            destinations[dest].append(route_id)
    
    # Process each destination
    for dest in sorted(destinations.keys()):
        dest_routes = destinations[dest]
        dest_clean = dest.replace("Client_", "")
        
        # Primary routes (had flow in original)
        primary_routes = [r for r in dest_routes if initial_flows.get(r, 0) > 0]
        backup_routes = [r for r in dest_routes if initial_flows.get(r, 0) == 0 and new_flows.get(r, 0) > 0]
        
        for route_id in primary_routes:
            old_qty = initial_flows.get(route_id, 0)
            new_qty = new_flows.get(route_id, 0)
            
            # Determine status
            if old_qty > 0 and new_qty == 0:
                status = "🔴 STOPPED"
            elif old_qty == 0 and new_qty > 0:
                status = "🟢 ACTIVATED"
            elif abs(old_qty - new_qty) < 0.01:
                if route_id in disrupted_route_ids:
                    status = "⚠️ Higher Cost (Forced)"
                else:
                    status = "⚪ UNCHANGED"
            elif old_qty > 0 and new_qty > 0:
                status = "🟡 Balanced"
            else:
                status = "⚪ UNCHANGED"
            
            rows.append({
                'Route Strategy': f"To {dest_clean}",
                'Original Plan (Standard)': f"Route {route_id}: {int(old_qty)} Units",
                'New Mitigation Plan (Post-Alert)': f"Route {route_id}: {int(new_qty)} Units",
                'Status': status
            })
        
        # Backup routes
        for route_id in backup_routes:
            new_qty = new_flows.get(route_id, 0)
            
            rows.append({
                'Route Strategy': f"(Backup {dest_clean})",
                'Original Plan (Standard)': f"Route {route_id}: 0 Units",
                'New Mitigation Plan (Post-Alert)': f"Route {route_id}: {int(new_qty)} Units",
                'Status': "🟢 ACTIVATED"
            })
    
    # Create DataFrame and export
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    
    return df, output_path


def main():
    print("\n" + "="*70)
    print("  CSV EXPORT DEMO - Supply Chain Risk Mitigation Report")
    print("="*70 + "\n")
    
    # Your logistics alert
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
    
    print("📋 Processing logistics alert...")
    
    # Step 1: Extract disruptions
    extractor = DisruptionExtractor()
    events = extractor.extract_from_text(logistics_alert)
    disruptions = [e.to_dict() for e in events]
    
    print(f"✅ Extracted {len(disruptions)} disruption(s)\n")
    
    # Step 2: Optimize
    optimizer = TransportOptimizer()
    baseline = optimizer.solve(use_disrupted_costs=False)
    optimizer.apply_disruptions(disruptions)
    adjusted = optimizer.solve(use_disrupted_costs=True)
    
    print(f"✅ Optimization complete")
    print(f"   - Original Cost: ${baseline['total_cost']:,.2f}")
    print(f"   - Adjusted Cost: ${adjusted['total_cost']:,.2f}")
    print(f"   - Increase: ${adjusted['total_cost'] - baseline['total_cost']:,.2f}\n")
    
    # Step 3: Export to CSV
    print("📊 Exporting to CSV format...")
    df, csv_path = export_to_csv_format(baseline, adjusted, disruptions, ROUTE_MAP)
    
    print(f"✅ Exported to: {csv_path}\n")
    
    # Display the table
    print("="*70)
    print("CSV CONTENT PREVIEW:")
    print("="*70)
    print(df.to_string(index=False))
    print("="*70 + "\n")
    
    # Also generate the narrative report
    summary_text, impact_table, cost_delta_pct = generate_impact_report(
        initial_solution=baseline,
        new_solution=adjusted,
        route_map=ROUTE_MAP,
        disruptions=disruptions
    )
    
    print("🎯 STRATEGIC NARRATIVE:")
    print("-" * 70)
    print(summary_text)
    print("-" * 70 + "\n")
    
    print(f"💡 Next Steps:")
    print(f"   1. Open {csv_path} in Excel or any spreadsheet application")
    print(f"   2. Share with supply chain management team")
    print(f"   3. Use for executive reporting and decision-making\n")


if __name__ == "__main__":
    main()
