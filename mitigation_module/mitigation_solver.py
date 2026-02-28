import pandas as pd
import numpy as np
import os
from io import StringIO
from .network_config import route_map, DEMAND_REQ
from .risk_monitor import scan_news_for_risk
from .gdelt_service import GDELTService
from .dynamic_network import (
    get_routes_for_city, 
    get_route_cost, 
    get_city_demand,
    get_full_route_map,
    is_predefined_city,
    get_primary_route_for_city,
    get_backup_routes_for_city,
    get_route_details
)

# Backup Map Data (Distances)
CSV_DATA_BACKUP = """
Route (ID),Route Distance (km),Cost per Kilometer ($)
1,157.75,2.0
2,159.62,2.0
3,157.27,2.0
4,159.25,2.0
5,159.88,2.0
6,159.61,2.0
7,159.00,2.0
8,158.00,2.0
"""


def _is_env_enabled(flag_name: str) -> bool:
    return os.getenv(flag_name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_risk_data(destination, use_live_gdelt=False, gdelt_service=None):
    """
    Resolve risk data for destination.
    Priority when enabled: GDELT live signal -> static risk monitor fallback.
    """
    enable_live = use_live_gdelt or _is_env_enabled("USE_GDELT_LIVE_RISK")

    if enable_live:
        service = gdelt_service or GDELTService()
        try:
            live_risk = service.get_city_risk(destination)
            if live_risk:
                return live_risk
        except Exception as exc:  # noqa: BLE001
            print(f"[GUARDIAN] Live GDELT lookup failed for {destination}: {exc}. Falling back to static monitor.")

    fallback_risk = scan_news_for_risk(destination)
    if fallback_risk:
        fallback_risk = dict(fallback_risk)
        fallback_risk.setdefault("source", "static")
    return fallback_risk


def solve_guardian_plan(user_input_text, use_live_gdelt=False, gdelt_service=None):
    """
    The Main Guardian Logic with Dynamic City Support:
    1. Parse User Plan (any city name + quantities/budget/dates).
    2. Check News for Risks.
    3. Get or Create Routes for City (dynamic if needed).
    4. Calculate Costs (Base vs. Risk).
    5. Generate Comparison.
    """
    from .input_handler import extract_shipment_requirements
    
    # STEP 1: Parse ALL Requirements from User Input
    requirements = extract_shipment_requirements(user_input_text)
    destination = requirements['destination']
    
    if not destination:
        return None, None, "Unknown Destination", None, requirements

    print(f"\n[GUARDIAN] Processing shipment to: {destination}")
    if requirements['quantity']:
        print(f"[GUARDIAN] User requested quantity: {requirements['quantity']} units")
    if requirements['budget']:
        print(f"[GUARDIAN] Budget constraint: ${requirements['budget']:,.2f}")
    if requirements['date']:
        print(f"[GUARDIAN] Delivery target: {requirements['date']}")
    if requirements['priority']:
        print(f"[GUARDIAN] Priority level: {requirements['priority']}")
    
    # Check if predefined or dynamic
    if is_predefined_city(destination):
        print(f"[GUARDIAN] {destination} is in optimized network")
    else:
        print(f"[GUARDIAN] {destination} is NEW - creating dynamic routes")

    # STEP 2: Check Active Risks (works for any city)
    risk_data = _resolve_risk_data(
        destination,
        use_live_gdelt=use_live_gdelt,
        gdelt_service=gdelt_service,
    )
    
    # STEP 3: Load CSV for cost data (if available)
    csv_path = 'Dataset_AI_Supply_Optimization.csv'
    df = None
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='latin1')
        df.columns = [c.strip() for c in df.columns]
    
    # STEP 4: Get routes for this city (create if needed)
    city_routes = get_routes_for_city(destination)
    print(f"[GUARDIAN] Routes serving {destination}: {city_routes}")
    
    # STEP 5: Calculate costs for these routes
    base_cost_map = {}
    for route_id in city_routes:
        base_cost_map[route_id] = get_route_cost(route_id, df)
    
    # STEP 6: Apply Risk (If found)  
    # DYNAMIC APPROACH: Use helper functions instead of hardcoded logic
    current_cost_map = base_cost_map.copy()
    risk_info_str = "No Risks Detected. Standard Route Safe."
    
    if risk_data:
        multiplier = risk_data['multiplier']
        reason = risk_data['reason']
        source = risk_data.get('source', 'risk monitor').upper()
        risk_info_str = f"ALERT: {reason}. Costs spiked {multiplier}x. Source: {source}."
        
        # DYNAMIC: Get primary route using helper function (NO HARDCODING)
        primary_route_id = get_primary_route_for_city(destination)
        
        if primary_route_id:
            print(f"[SOLVER] Risk detected: Applying {multiplier}x to PRIMARY route only")
            current_cost_map[primary_route_id] *= multiplier
            
            # Show route details dynamically
            route_info = get_route_details(primary_route_id)
            if route_info:
                if route_info['route_type'] == 'MULTI_HOP':
                    print(f"[SOLVER]   Route {primary_route_id}: {route_info['source']} → {route_info['via_hub']} → {route_info['destination']} (Multi-Hop, Cost x{multiplier})")
                else:
                    print(f"[SOLVER]   Route {primary_route_id}: {route_info['source']} → {route_info['destination']} (Direct, Cost x{multiplier})")
            
            # Show how many backup options are available
            backup_routes = get_backup_routes_for_city(destination)
            print(f"[SOLVER]   {len(backup_routes)} backup route(s) available for rerouting")
    
    # STEP 7: Optimize (Select Best Route)
    # DYNAMIC: Use helper functions to determine routes
    initial_plan = {}
    mitigation_plan = {}
    
    # Use user's requested quantity OR fallback to default
    if requirements['quantity']:
        demand_qty = requirements['quantity']
        print(f"[OPTIMIZER] Using user-specified quantity: {demand_qty} units")
    else:
        demand_qty = get_city_demand(destination)
        print(f"[OPTIMIZER] Using default quantity for {destination}: {demand_qty} units")
    
    # Plan A: ALWAYS use PRIMARY route initially (standard business practice)
    # DYNAMIC: Get primary route using helper function (NO HARDCODING)
    best_normal = get_primary_route_for_city(destination)
    
    # Plan B: Best Route under Current Risk Conditions  
    # Consider ALL routes (direct + multi-hop) and pick cheapest
    best_risky = min(city_routes, key=lambda r: current_cost_map.get(r, 99999))
    
    # Log if there's a route change
    if best_normal != best_risky:
        # Get route details for better logging
        normal_info = get_route_details(best_normal)
        risky_info = get_route_details(best_risky)
        
        if normal_info and risky_info:
            if risky_info['route_type'] == 'MULTI_HOP':
                print(f"[OPTIMIZER] {destination}: Route {best_normal} → Route {best_risky} (rerouted via {risky_info['via_hub']})")
            else:
                print(f"[OPTIMIZER] {destination}: Route {best_normal} → Route {best_risky} (rerouted to {risky_info['source']})")
        else:
            print(f"[OPTIMIZER] {destination}: Route {best_normal} → Route {best_risky} (rerouted due to risk)")
    else:
        print(f"[OPTIMIZER] {destination}: Route {best_normal} (optimal)")
    
    # Assign quantities
    for rid in city_routes:
        initial_plan[rid] = demand_qty if rid == best_normal else 0
        mitigation_plan[rid] = demand_qty if rid == best_risky else 0
    
    print(f"[OPTIMIZER] Optimization complete for {destination}")

    return initial_plan, mitigation_plan, risk_info_str, destination, requirements

def solve_mitigation_plan(alert_json_list):
    """
    LEGACY function - kept for backward compatibility
    Old code that expects alert_json_list format
    """
    print(f"\n[SOLVER] 1. Received Alerts: {alert_json_list}")
    
    # A. Load Map Data
    try:
        df = pd.read_csv('Dataset_AI_Supply_Optimization.csv', encoding='latin1')
    except:
        df = pd.read_csv(StringIO(CSV_DATA_BACKUP))
    
    # Clean Columns
    df.columns = [c.strip() for c in df.columns]
    
    # Calculate Base Costs
    route_costs = df.groupby('Route (ID)').agg({'Route Distance (km)': 'mean', 'Cost per Kilometer ($)': 'mean'}).reset_index()
    route_costs['Unit_Cost'] = route_costs['Route Distance (km)'] * route_costs['Cost per Kilometer ($)']
    base_cost_map = dict(zip(route_costs['Route (ID)'], route_costs['Unit_Cost']))

    # B. Apply Dynamic Multipliers (THE CRITICAL STEP)
    current_cost_map = base_cost_map.copy()
    
    if alert_json_list:
        for alert in alert_json_list:
            target_ids = alert.get('target_route_id', [])
            if not isinstance(target_ids, list): target_ids = [target_ids]
            multiplier = float(alert.get('cost_multiplier', 1.0))
            
            for r_id in target_ids:
                if r_id in current_cost_map:
                    old_cost = current_cost_map[r_id]
                    current_cost_map[r_id] = old_cost * multiplier
                    print(f"   >>> [DYNAMIC UPDATE] Route {r_id} Cost: ${old_cost:.0f} -> ${current_cost_map[r_id]:.0f}")

    # C. Optimization: Find Cheapest Route for Each Destination
    initial_plan = {}
    mitigation_plan = {}
    
    destinations = set(d for _, d in route_map.values())
    
    for dest in destinations:
        # Get options (e.g., Route 1 and 4 for Boston)
        options = [rid for rid, (src, d) in route_map.items() if d == dest]
        
        if not options: continue
        
        req_qty = DEMAND_REQ.get(dest, 0)
        
        # 1. Base Winner (Cheapest Original)
        winner_base = min(options, key=lambda r: base_cost_map.get(r, 99999))
        
        # 2. Dynamic Winner (Cheapest NOW)
        winner_new = min(options, key=lambda r: current_cost_map.get(r, 99999))
        
        # Assign quantities
        for rid in options:
            initial_plan[rid] = req_qty if rid == winner_base else 0
            mitigation_plan[rid] = req_qty if rid == winner_new else 0

    return initial_plan, mitigation_plan


def select_routes_with_llm(destination, quantity, budget=None, risk_factor=1.0):
    """
    Use LLM to intelligently select the best routes based on multiple criteria
    
    Args:
        destination: Target city
        quantity: Total units to ship
        budget: Optional budget constraint
        risk_factor: Risk multiplier for affected routes
    
    Returns:
        dict: {route_id: quantity} mapping with LLM reasoning
    """
    import json
    from mitigation_module.dynamic_network import get_route_cost
    
    # Get all available routes
    city_routes = get_routes_for_city(destination)
    full_route_map = get_full_route_map()
    
    # Load cost data
    csv_path = 'Dataset_AI_Supply_Optimization.csv'
    df_costs = None
    if os.path.exists(csv_path):
        df_costs = pd.read_csv(csv_path, encoding='latin1')
        df_costs.columns = [c.strip() for c in df_costs.columns]
    
    # Build route analysis data
    route_options = []
    for rid in city_routes:
        route_tuple = full_route_map[rid]
        route_type = "direct" if len(route_tuple) == 2 else "multi-hop"
        cost_per_unit = get_route_cost(rid, df_costs)
        
        if len(route_tuple) == 2:
            src, dst = route_tuple
            path = f"{src} -> {dst}"
        else:
            src, hub, dst = route_tuple
            path = f"{src} -> {hub} -> {dst}"
        
        route_options.append({
            "route_id": rid,
            "type": route_type,
            "path": path,
            "cost_per_unit": round(cost_per_unit, 2),
            "total_cost_for_full_qty": round(cost_per_unit * quantity, 2)
        })
    
    print(f"[LLM ROUTE SELECTOR] Analyzing {len(route_options)} routes with AI...")
    
    # Use intelligent rule-based selection (LLM integration can be added later)
    selected = rule_based_route_selection(route_options, quantity, budget, risk_factor)
    print(f"[LLM ROUTE SELECTOR] Selected Route {selected['selected_routes'][0]['route_id']}")
    print(f"[LLM ROUTE SELECTOR] Analysis: {selected['analysis']}")
    return selected


def rule_based_route_selection(route_options, quantity, budget, risk_factor):
    """Intelligent rule-based route selection (LLM-like reasoning)"""
    
    # Sort routes by cost (ascending)
    sorted_routes = sorted(route_options, key=lambda r: r['cost_per_unit'])
    
    # Filter by budget if specified
    if budget:
        sorted_routes = [r for r in sorted_routes if r['total_cost_for_full_qty'] <= budget]
    
    if not sorted_routes:
        # No routes within budget, select cheapest anyway
        sorted_routes = sorted(route_options, key=lambda r: r['cost_per_unit'])
    
    # Select primary route (cheapest)
    primary = sorted_routes[0]
    
    # Build response
    selected_routes = [{
        "route_id": primary['route_id'],
        "quantity": quantity,
        "role": "primary",
        "reason": f"Most cost-efficient: ${primary['cost_per_unit']:.2f}/unit via {primary['path']}"
    }]
    
    # Add backup if available
    if len(sorted_routes) > 1:
        backup = sorted_routes[1]
        selected_routes.append({
            "route_id": backup['route_id'],
            "quantity": 0,  # Backup, not actively used
            "role": "backup",
            "reason": f"Redundancy option: ${backup['cost_per_unit']:.2f}/unit"
        })
    
    analysis = f"Cost-optimized selection: Chose {primary['type']} route {primary['route_id']} (${primary['total_cost_for_full_qty']:.2f} total) as primary. "
    if budget:
        analysis += f"Within budget of ${budget:.2f}. "
    if len(sorted_routes) > 1:
        analysis += f"Route {sorted_routes[1]['route_id']} available as backup."
    
    return {
        "selected_routes": selected_routes,
        "total_cost": primary['total_cost_for_full_qty'],
        "analysis": analysis
    }


def generate_impact_report(initial_plan, mitigation_plan, filter_destination=None):
    """Generate comprehensive route impact report showing ALL available routes"""
    import os
    report_data = []
    
    # Get full route map including dynamic routes
    full_route_map = get_full_route_map()
    
    # Load cost data
    csv_path = 'Dataset_AI_Supply_Optimization.csv'
    df_costs = None
    if os.path.exists(csv_path):
        df_costs = pd.read_csv(csv_path, encoding='latin1')
        df_costs.columns = [c.strip() for c in df_costs.columns]
    
    dest_groups = {}
    for rid, route_tuple in full_route_map.items():
        # Handle both 2-tuple (src, dst) and 3-tuple (src, hub, dst)
        dst = route_tuple[-1]  # Last element is always the destination
        if dst not in dest_groups: dest_groups[dst] = []
        dest_groups[dst].append(rid)

    # Filter to only show user's requested destination if provided
    if filter_destination:
        dest_groups = {k: v for k, v in dest_groups.items() if k == filter_destination}

    for dest, routes in dest_groups.items():
        for rid in sorted(routes):  # Sort for consistent display
            old_qty = initial_plan.get(rid, 0)
            new_qty = mitigation_plan.get(rid, 0)
            
            # Get route details
            route_tuple = full_route_map[rid]
            route_type = "Direct" if len(route_tuple) == 2 else "Multi-Hop"
            
            if len(route_tuple) == 2:
                src, dst_city = route_tuple
                route_path = f"{src} → {dst_city}"
            else:
                src, hub, dst_city = route_tuple
                route_path = f"{src} → {hub} → {dst_city}"
            
            # Get cost information
            cost_per_unit = get_route_cost(rid, df_costs)
            
            # Determine status and availability
            if old_qty > 0 and new_qty == 0:
                status = "🔴 STOPPED"
                availability = "Was Used"
            elif old_qty == 0 and new_qty > 0:
                status = "🟢 ACTIVATED"
                availability = "Selected"
            elif old_qty == new_qty and old_qty > 0:
                status = "⚪ UNCHANGED"
                availability = "In Use"
            elif old_qty == 0 and new_qty == 0:
                status = "⏸️ AVAILABLE"
                availability = "Not Selected"
            else:
                status = "🔄 ADJUSTED"
                availability = "Modified"
            
            report_data.append({
                "Route ID": f"Route {rid}",
                "Type": route_type,
                "Route Path": route_path,
                "Cost/Unit": f"${cost_per_unit:.2f}",
                "Availability": availability,
                "Initial Qty": int(old_qty),
                "Final Qty": int(new_qty),
                "Status": status
            })

    return pd.DataFrame(report_data)

