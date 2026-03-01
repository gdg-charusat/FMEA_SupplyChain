"""
Report Generator for Supply Chain Risk Mitigation
Produces narrative-driven, user-friendly visualizations of route optimization changes
"""

import pandas as pd
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


# Module-level tolerance for quantity comparisons (centralized).
_QUANTITY_TOLERANCE = 0.01


def _format_quantity(qty: float) -> str:
    """
    Format quantity for display, showing decimals only when needed.
    
    Examples:
        10.0 -> "10"
        10.5 -> "10.5"
        10.50 -> "10.5"
        10.123 -> "10.12"
    """
    # Use a tiny tolerance to avoid floating-point equality pitfalls
    if abs(qty - int(qty)) < 1e-9:
        return str(int(qty))
    else:
        # Show up to 2 decimal places, strip trailing zeros
        formatted = f"{qty:.2f}".rstrip('0').rstrip('.')
        return formatted


def generate_impact_report(
    initial_solution: Dict,
    new_solution: Dict,
    route_map: Dict[int, Tuple[str, str]],
    disruptions: List[Dict] = None
) -> Tuple[str, pd.DataFrame, float]:
    """
    Generate a narrative-driven impact report comparing original vs optimized plans.
    
    Args:
        initial_solution: Dict with 'flows' (route_id -> quantity) and 'total_cost'
        new_solution: Dict with 'flows' (route_id -> quantity) and 'total_cost'
        route_map: Dict mapping route_id to (source, destination) tuples
        disruptions: List of disruption events with route_id and cost_multiplier
    
    Returns:
        Tuple of (summary_text, impact_table, cost_delta_pct)
    """
    
    # Extract flows and costs
    initial_flows = initial_solution.get('flows', {})
    new_flows = new_solution.get('flows', {})
    initial_cost = initial_solution.get('total_cost', 0)
    new_cost = new_solution.get('total_cost', 0)
    
    # Calculate cost delta
    cost_delta = new_cost - initial_cost
    cost_delta_pct = (cost_delta / initial_cost * 100) if initial_cost > 0 else 0
    
    # Identify disrupted routes
    disrupted_routes = []
    max_multiplier = 1.0
    if disruptions:
        for d in disruptions:
            route_id = d.get('target_route_id')
            multiplier = d.get('cost_multiplier', 1.0)
            if multiplier > max_multiplier:
                max_multiplier = multiplier
            if multiplier > 1.0:
                disrupted_routes.append(route_id)
    
    # Generate narrative text
    summary_text = _generate_narrative(
        disrupted_routes, 
        initial_flows, 
        new_flows, 
        route_map,
        cost_delta_pct,
        max_multiplier
    )
    
    # Generate impact table
    impact_table = _generate_impact_table(
        initial_flows,
        new_flows,
        route_map,
        disrupted_routes
    )
    
    return summary_text, impact_table, cost_delta_pct


def _generate_narrative(
    disrupted_routes: List[int],
    initial_flows: Dict[int, float],
    new_flows: Dict[int, float],
    route_map: Dict[int, Tuple[str, str]],
    cost_delta_pct: float,
    max_multiplier: float
) -> str:
    """Generate dynamic narrative text about the optimization changes."""
    
    narrative_parts = []
    
    # Part 1: Disruption detection
    if disrupted_routes:
        route_names = []
        for r_id in disrupted_routes:
            if r_id in route_map:
                source, dest = route_map[r_id]
                route_names.append(f"Route {r_id} ({dest.replace('Client_', '')})")
        
        route_list = ", ".join(route_names) if route_names else f"Route {disrupted_routes}"
        
        multiplier_text = f"{max_multiplier:.1f}x" if max_multiplier > 1 else "significantly"
        
        narrative_parts.append(
            f"🚨 **ALERT DETECTED**: Your system has identified that {route_list} "
            f"{'are' if len(disrupted_routes) > 1 else 'is'} now experiencing disruptions "
            f"with cost increases of {multiplier_text}."
        )
    
    # Part 2: Activation status
    stopped_routes = []
    activated_routes = []
    balanced_routes = []
    
    all_routes = set(list(initial_flows.keys()) + list(new_flows.keys()))
    for route_id in all_routes:
        old_qty = initial_flows.get(route_id, 0)
        new_qty = new_flows.get(route_id, 0)
        
        if old_qty > 0 and new_qty == 0:
            stopped_routes.append(route_id)
        elif old_qty == 0 and new_qty > 0:
            activated_routes.append(route_id)
        elif abs(old_qty - new_qty) > 0.01 and old_qty > 0 and new_qty > 0:
            balanced_routes.append(route_id)
    
    # Determine strategy type
    if activated_routes or stopped_routes:
        # Routes were changed - true mitigation
        if activated_routes:
            backup_list = ", ".join([f"Route {r}" for r in activated_routes])
            narrative_parts.append(
                f"✅ **BACKUP ACTIVATED**: The system has automatically activated backup routes: {backup_list}."
            )
        
        if stopped_routes:
            stopped_list = ", ".join([f"Route {r}" for r in stopped_routes])
            narrative_parts.append(
                f"🔴 **ROUTES SUSPENDED**: The following primary routes have been stopped: {stopped_list}."
            )
    elif disrupted_routes:
        # No routes changed but costs increased - forced to use expensive routes
        route_list = ", ".join([f"Route {r}" for r in disrupted_routes if r in initial_flows and initial_flows[r] > 0])
        if route_list:
            narrative_parts.append(
                f"⚠️ **FORCED CONTINUATION**: Despite the disruptions, the system must continue using {route_list} "
                f"as no alternative routes are available with sufficient capacity. This results in increased operational costs."
            )
    
    if balanced_routes:
        balanced_list = ", ".join([f"Route {r}" for r in balanced_routes])
        narrative_parts.append(
            f"🟡 **ROUTES REBALANCED**: The following routes had quantity adjustments: {balanced_list}."
        )
    
    # Part 3: Cost impact
    if cost_delta_pct > 0:
        from_flows = initial_flows if isinstance(initial_flows, dict) else {}
        to_flows = new_flows if isinstance(new_flows, dict) else {}
        
        # Calculate actual cost delta from the cost values, not flows
        narrative_parts.append(
            f"💰 **COST IMPACT**: The mitigation strategy will increase total logistics cost by "
            f"{cost_delta_pct:.1f}%. This is unavoidable given current network constraints and disruption severity."
        )
    else:
        narrative_parts.append(
            f"✅ **COST OPTIMIZED**: The new plan maintains cost efficiency with minimal impact."
        )
    
    return "\n\n".join(narrative_parts)


def _generate_impact_table(
    initial_flows: Dict[int, float],
    new_flows: Dict[int, float],
    route_map: Dict[int, Tuple[str, str]],
    disrupted_routes: List[int]
) -> pd.DataFrame:
    """
    Generate formatted impact table grouped by destination.
    CRITICAL FIX: Ensures disrupted routes appear even if flow = 0
    
    Returns DataFrame with columns:
    - Route Strategy (Destination + Route Info)
    - Original Plan (Standard)
    - New Mitigation Plan (Post-Alert)
    - Status
    """
    
    rows = []
    
    # Get all unique destinations - INCLUDE disrupted routes even with 0 flow
    destinations = {}
    
    # Add all routes with any flow
    all_routes = set(list(initial_flows.keys()) + list(new_flows.keys()))
    
    # CRITICAL: Add disrupted routes even if they have 0 flow in both plans
    all_routes.update(disrupted_routes)
    
    for route_id in all_routes:
        if route_id in route_map:
            source, dest = route_map[route_id]
            if dest not in destinations:
                destinations[dest] = []
            destinations[dest].append(route_id)
    
    # Sort destinations alphabetically
    # Use module-level tolerance for consistency
    
    for dest in sorted(destinations.keys()):
        dest_routes = destinations[dest]
        
        # Separate primary (had flow in original) vs backup (no flow in original)
        primary_routes = [r for r in dest_routes if initial_flows.get(r, 0) > _QUANTITY_TOLERANCE]
        backup_routes = [r for r in dest_routes if initial_flows.get(r, 0) < _QUANTITY_TOLERANCE and new_flows.get(r, 0) > _QUANTITY_TOLERANCE]
        
        # Clean destination name
        dest_clean = dest.replace("Client_", "").replace("_", " ")
        
        # Add primary routes first
        for route_id in primary_routes:
            old_qty = initial_flows.get(route_id, 0)
            new_qty = new_flows.get(route_id, 0)
            
            status = _determine_status(old_qty, new_qty)
            
            # Add disruption indicator
            is_disrupted = route_id in disrupted_routes
            route_strategy = f"To {dest_clean}"
            if is_disrupted:
                route_strategy = f"⚠️ To {dest_clean}"
            
            # Format quantities with disruption warning (preserve decimals)
            original_plan = f"Route {route_id}: {_format_quantity(old_qty)} Units"
            if is_disrupted and old_qty > 0 and new_qty > 0 and abs(old_qty - new_qty) < _QUANTITY_TOLERANCE:
                # Same flow but disrupted - show cost impact
                new_plan = f"Route {route_id}: {_format_quantity(new_qty)} Units (⚠️ Higher Cost)"
            elif new_qty > 0 and old_qty > 0 and abs(new_qty - old_qty) >= _QUANTITY_TOLERANCE:
                # Balanced - show split
                new_plan = f"Route {route_id}: {_format_quantity(new_qty)} Units"
            else:
                new_plan = f"Route {route_id}: {_format_quantity(new_qty)} Units" if new_qty > _QUANTITY_TOLERANCE else f"Route {route_id}: 0 Units"
            
            rows.append({
                'Route Strategy': route_strategy,
                'Original Plan (Standard)': original_plan,
                'New Mitigation Plan (Post-Alert)': new_plan,
                'Status': status
            })
        
        # Add backup routes
        for route_id in backup_routes:
            old_qty = 0
            new_qty = new_flows.get(route_id, 0)
            
            status = _determine_status(old_qty, new_qty)
            
            route_strategy = f"(Backup {dest_clean})"
            
            rows.append({
                'Route Strategy': route_strategy,
                'Original Plan (Standard)': f"Route {route_id}: 0 Units",
                'New Mitigation Plan (Post-Alert)': f"Route {route_id}: {_format_quantity(new_qty)} Units",
                'Status': status
            })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    if df.empty:
        # Return empty DataFrame with proper columns
        df = pd.DataFrame(columns=[
            'Route Strategy',
            'Original Plan (Standard)',
            'New Mitigation Plan (Post-Alert)',
            'Status'
        ])
    
    return df


def _determine_status(old_qty: float, new_qty: float) -> str:
    """Determine status emoji based on quantity changes with float tolerance."""
    # Use consistent float tolerance (module-level)
    if old_qty > _QUANTITY_TOLERANCE and new_qty < _QUANTITY_TOLERANCE:
        return "🔴 STOPPED"
    elif old_qty < _QUANTITY_TOLERANCE and new_qty > _QUANTITY_TOLERANCE:
        return "🟢 ACTIVATED"
    elif abs(old_qty - new_qty) < _QUANTITY_TOLERANCE:
        return "⚪ UNCHANGED"
    elif old_qty > _QUANTITY_TOLERANCE and new_qty > _QUANTITY_TOLERANCE:
        return "🟡 BALANCED"
    else:
        return "⚪ UNCHANGED"


def format_for_streamlit(impact_table: pd.DataFrame) -> pd.DataFrame:
    """
    Format the impact table for optimal Streamlit display with styling.
    
    Args:
        impact_table: DataFrame from generate_impact_report
    
    Returns:
        Styled DataFrame ready for st.dataframe()
    """
    
    # No modifications needed - Streamlit handles emoji rendering
    # Just return the dataframe as-is
    return impact_table


def get_route_change_summary(
    initial_flows: Dict[int, float],
    new_flows: Dict[int, float],
    route_map: Dict[int, Tuple[str, str]]
) -> Dict[str, int]:
    """
    Get summary counts of route status changes with float tolerance.
    
    Returns:
        Dict with counts: {'stopped': int, 'activated': int, 'balanced': int, 'unchanged': int}
    """
    
    # Use consistent float tolerance (module-level)
    counts = {'stopped': 0, 'activated': 0, 'balanced': 0, 'unchanged': 0}
    
    all_routes = set(list(initial_flows.keys()) + list(new_flows.keys()))
    
    for route_id in all_routes:
        old_qty = initial_flows.get(route_id, 0)
        new_qty = new_flows.get(route_id, 0)
        
        if old_qty > _QUANTITY_TOLERANCE and new_qty < _QUANTITY_TOLERANCE:
            counts['stopped'] += 1
        elif old_qty < _QUANTITY_TOLERANCE and new_qty > _QUANTITY_TOLERANCE:
            counts['activated'] += 1
        elif abs(old_qty - new_qty) < _QUANTITY_TOLERANCE:
            counts['unchanged'] += 1
        elif old_qty > _QUANTITY_TOLERANCE and new_qty > _QUANTITY_TOLERANCE:
            counts['balanced'] += 1
    
    return counts
