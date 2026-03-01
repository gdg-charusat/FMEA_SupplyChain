"""
DYNAMIC NETWORK CONFIGURATION - NO HARDCODING
Supports unlimited cities with multiple warehouses and multi-hop routing through hubs
"""

import pandas as pd
import threading
from .network_config import (
    route_map, DEMAND_REQ, WAREHOUSES, DISTRIBUTION_HUBS,
    DYNAMIC_ROUTE_START_ID, MULTIHOP_ROUTE_START_ID,
    PRIMARY_ROUTES, get_warehouse_list, get_hub_list
)

# Default costs when CSV doesn't have data
DEFAULT_DISTANCE_KM = 500
DEFAULT_COST_PER_KM = 2.0
DEFAULT_HUB_DISTANCE_KM = 300  # Distance from warehouse to hub
DEFAULT_HUB_TO_CITY_KM = 250   # Distance from hub to final destination
DEFAULT_DEMAND = 250

# ✅ THREAD SAFETY: Protected access to global route state
_route_state_lock = threading.RLock()  # Recursive lock for nested access

# Track dynamically created routes
_dynamic_direct_routes = {}  # city -> [route_ids] for direct routes
_dynamic_multihop_routes = {}  # city -> [route_ids] for multi-hop routes
_next_dynamic_id = DYNAMIC_ROUTE_START_ID
_next_multihop_id = MULTIHOP_ROUTE_START_ID


def is_predefined_city(city_name):
    """Check if city is in our predefined optimized network"""
    return city_name in DEMAND_REQ


def get_routes_for_city(city_name, include_multihop=True):
    """
    Get ALL route IDs serving a city (predefined + dynamic + multi-hop)
    FULLY DYNAMIC: Creates routes for ALL cities, including predefined ones!
    ✅ THREAD SAFE: Protected from race conditions
    
    Args:
        city_name: Destination city
        include_multihop: Whether to include multi-hop routes through hubs
    
    Returns:
        list of route IDs (direct routes + optional multi-hop routes)
    """
    all_routes = []
    
    # 1. Include predefined routes (Routes 1-10 from CSV) if they exist
    predefined = [rid for rid, (src, dst) in route_map.items() if dst == city_name]
    all_routes.extend(predefined)
    
    # ✅ FIX: Use lock to prevent race conditions
    with _route_state_lock:
        # 2. ALWAYS create dynamic DIRECT routes for ALL cities
        # This ensures EVERY city gets routes from ALL warehouses
        if city_name not in _dynamic_direct_routes:
            # Create new dynamic direct routes (one from EACH warehouse)
            created = create_direct_routes(city_name)
            all_routes.extend(created)
        else:
            all_routes.extend(_dynamic_direct_routes[city_name])
        
        # 3. ALWAYS create multi-hop routes for ALL cities
        # This provides alternative paths through distribution hubs
        if include_multihop:
            if city_name not in _dynamic_multihop_routes:
                # Create multi-hop routes through ALL hubs
                created = create_multihop_routes(city_name)
                all_routes.extend(created)
            else:
                all_routes.extend(_dynamic_multihop_routes[city_name])
    
    return all_routes


def create_direct_routes(city_name):
    """
    Create DIRECT routes from ALL warehouses to a city
    DYNAMIC: Automatically uses all warehouses defined in WAREHOUSES dict
    ✅ THREAD SAFE: Must be called within _route_state_lock context
    
    Args:
        city_name: Destination city
    
    Returns:
        list of route IDs created
    """
    global _next_dynamic_id
    
    route_ids = []
    warehouses = get_warehouse_list()  # Gets ALL warehouses dynamically
    
    print(f"[DYNAMIC NETWORK] Creating {len(warehouses)} direct routes to {city_name}")
    
    for warehouse in warehouses:
        route_id = _next_dynamic_id
        _next_dynamic_id += 1  # ✅ SAFE: Protected by _route_state_lock in caller
        
        # Store in dynamic route map
        if city_name not in _dynamic_direct_routes:
            _dynamic_direct_routes[city_name] = []
        _dynamic_direct_routes[city_name].append(route_id)
        
        route_ids.append(route_id)
        
        print(f"[DYNAMIC NETWORK]   Route {route_id}: {warehouse} → {city_name} (Direct)")
    
    return route_ids


def create_multihop_routes(city_name):
    """
    Create MULTI-HOP routes through intermediate distribution hubs
    Pattern: Warehouse → Hub → Destination City
    DYNAMIC: Automatically uses all hubs defined in DISTRIBUTION_HUBS dict
    ✅ THREAD SAFE: Must be called within _route_state_lock context
    
    Args:
        city_name: Destination city
    
    Returns:
        list of route IDs created (multi-hop)
    """
    global _next_multihop_id
    
    route_ids = []
    warehouses = get_warehouse_list()
    hubs = get_hub_list()
    
    print(f"[DYNAMIC NETWORK] Creating {len(warehouses) * len(hubs)} multi-hop routes to {city_name}")
    
    # Create routes: Each warehouse → Each hub → City
    for warehouse in warehouses:
        for hub in hubs:
            route_id = _next_multihop_id
            _next_multihop_id += 1  # ✅ SAFE: Protected by _route_state_lock in caller
            
            # Store in multi-hop route map
            if city_name not in _dynamic_multihop_routes:
                _dynamic_multihop_routes[city_name] = []
            _dynamic_multihop_routes[city_name].append(route_id)
            
            route_ids.append(route_id)
            
            print(f"[DYNAMIC NETWORK]   Route {route_id}: {warehouse} → {hub} → {city_name} (Multi-Hop)")
    
    return route_ids


def get_route_cost(route_id, csv_data=None):
    """
    Get cost for ANY route (predefined, direct dynamic, or multi-hop)
    DYNAMIC: Automatically calculates costs based on route type
    
    Args:
        route_id: Route ID to look up
        csv_data: Pandas DataFrame with route costs (optional)
    
    Returns:
        float: Total cost for the route
    """
    # 1. Predefined routes (1-10): Get from CSV if available
    if route_id in PRIMARY_ROUTES or route_id in route_map:
        if csv_data is not None and route_id in csv_data['Route (ID)'].values:
            route_cost = csv_data[csv_data['Route (ID)'] == route_id].iloc[0]
            distance = route_cost['Route Distance (km)']
            cost_per_km = route_cost['Cost per Kilometer ($)']
            return distance * cost_per_km
        # Fallback for predefined routes without CSV data
        return DEFAULT_DISTANCE_KM * DEFAULT_COST_PER_KM
    
    # 2. Dynamic direct routes (100-999): Standard cost
    elif DYNAMIC_ROUTE_START_ID <= route_id < MULTIHOP_ROUTE_START_ID:
        return DEFAULT_DISTANCE_KM * DEFAULT_COST_PER_KM
    
    # 3. Multi-hop routes (1000+): Calculate total distance through hub
    elif route_id >= MULTIHOP_ROUTE_START_ID:
        # Multi-hop: warehouse → hub + hub → destination
        leg1_cost = DEFAULT_HUB_DISTANCE_KM * DEFAULT_COST_PER_KM  # To hub
        leg2_cost = DEFAULT_HUB_TO_CITY_KM * DEFAULT_COST_PER_KM   # Hub to city
        return leg1_cost + leg2_cost
    
    # Unknown route: return default
    return DEFAULT_DISTANCE_KM * DEFAULT_COST_PER_KM


def get_route_details(route_id):
    """
    Get detailed information about a route
    Returns: dict with source, destination, route_type, hops, etc.
    ✅ THREAD SAFE: Protected from race conditions
    """
    # Check predefined routes
    if route_id in route_map:
        src, dst = route_map[route_id]
        return {
            "route_id": route_id,
            "source": src,
            "destination": dst,
            "route_type": "PREDEFINED",
            "hops": 1,
            "via_hub": None,
            "is_primary": route_id in PRIMARY_ROUTES
        }
    
    # ✅ FIX: Use lock to prevent race conditions while reading
    with _route_state_lock:
        # Check dynamic direct routes
        for city, route_list in _dynamic_direct_routes.items():
            if route_id in route_list:
                idx = route_list.index(route_id)
                warehouses = get_warehouse_list()
                warehouse = warehouses[idx % len(warehouses)]
                return {
                    "route_id": route_id,
                    "source": warehouse,
                    "destination": city,
                    "route_type": "DYNAMIC_DIRECT",
                    "hops": 1,
                    "via_hub": None,
                    "is_primary": idx == 0  # First warehouse is primary
                }
        
        # Check multi-hop routes
        for city, route_list in _dynamic_multihop_routes.items():
            if route_id in route_list:
                idx = route_list.index(route_id)
                warehouses = get_warehouse_list()
                hubs = get_hub_list()
                
                warehouse_idx = idx // len(hubs)
                hub_idx = idx % len(hubs)
                
                warehouse = warehouses[warehouse_idx % len(warehouses)]
                hub = hubs[hub_idx]
                
                return {
                    "route_id": route_id,
                    "source": warehouse,
                    "destination": city,
                    "route_type": "MULTI_HOP",
                    "hops": 2,
                    "via_hub": hub,
                    "is_primary": False  # Multi-hop routes are always alternatives
                }
    
    return None


def get_city_demand(city_name):
    """Get demand for a city (predefined or default)"""
    return DEMAND_REQ.get(city_name, DEFAULT_DEMAND)


def get_full_route_map(include_dynamic=True, include_multihop=True):
    """
    Get complete route map including ALL routes (predefined + dynamic + multi-hop)
    DYNAMIC: Automatically includes all generated routes
    ✅ THREAD SAFE: Protected from race conditions
    
    Args:
        include_dynamic: Include dynamically created direct routes
        include_multihop: Include multi-hop routes through hubs
    
    Returns:
        dict mapping route_id -> (source, destination) or (source, hub, destination)
    """
    # ✅ FIX: Use lock to prevent reading while another thread is writing
    with _route_state_lock:
        full_map = route_map.copy()
        
        # Add dynamic direct routes
        if include_dynamic:
            for city_name, route_ids in _dynamic_direct_routes.items():
                warehouses = get_warehouse_list()
                for idx, route_id in enumerate(route_ids):
                    warehouse = warehouses[idx % len(warehouses)]
                    full_map[route_id] = (warehouse, city_name)
        
        # Add multi-hop routes
        if include_multihop:
            for city_name, route_ids in _dynamic_multihop_routes.items():
                warehouses = get_warehouse_list()
                hubs = get_hub_list()
                
                for idx, route_id in enumerate(route_ids):
                    warehouse_idx = idx // len(hubs)
                    hub_idx = idx % len(hubs)
                    
                    warehouse = warehouses[warehouse_idx % len(warehouses)]
                    hub = hubs[hub_idx]
                    
                    # For multi-hop, store as tuple (warehouse, hub, city)
                    full_map[route_id] = (warehouse, hub, city_name)
        
        return full_map


def get_primary_route_for_city(city_name):
    """
    Get the PRIMARY (preferred) route for a city
    Priority: Predefined primary > First warehouse direct route
    """
    routes = get_routes_for_city(city_name, include_multihop=False)
    
    if not routes:
        return None
    
    # Check if any are predefined primary routes
    for route_id in routes:
        if route_id in PRIMARY_ROUTES:
            return route_id
    
    # Return first direct route (from highest priority warehouse)
    direct_routes = [r for r in routes if r < MULTIHOP_ROUTE_START_ID]
    return direct_routes[0] if direct_routes else routes[0]


def get_backup_routes_for_city(city_name):
    """
    Get all BACKUP/ALTERNATIVE routes for a city (excluding primary)
    Returns list of route IDs for rerouting options
    """
    all_routes = get_routes_for_city(city_name, include_multihop=True)
    primary = get_primary_route_for_city(city_name)
    
    return [r for r in all_routes if r != primary]


def reset_dynamic_routes():
    """
    Clear all dynamically created routes (for testing)
    ✅ THREAD SAFE: Protected from race conditions
    """
    global _dynamic_direct_routes, _dynamic_multihop_routes, _next_dynamic_id, _next_multihop_id
    
    with _route_state_lock:
        _dynamic_direct_routes = {}
        _dynamic_multihop_routes = {}
        _next_dynamic_id = DYNAMIC_ROUTE_START_ID
        _next_multihop_id = MULTIHOP_ROUTE_START_ID
    
    print("[DYNAMIC NETWORK] Reset: All dynamic and multi-hop routes cleared")


def get_network_summary():
    """
    Get comprehensive summary of current network state
    ✅ THREAD SAFE: Protected from race conditions
    """
    # ✅ FIX: Use lock to ensure consistent snapshot of state
    with _route_state_lock:
        predefined_cities = len(DEMAND_REQ)
        dynamic_cities = len(_dynamic_direct_routes)
        total_warehouses = len(WAREHOUSES)
        total_hubs = len(DISTRIBUTION_HUBS)
        
        direct_route_count = sum(len(routes) for routes in _dynamic_direct_routes.values())
        multihop_route_count = sum(len(routes) for routes in _dynamic_multihop_routes.values())
        total_routes = len(route_map) + direct_route_count + multihop_route_count
    
    return {
        "network_type": "DYNAMIC (No Hardcoding)",
        "warehouses": total_warehouses,
        "distribution_hubs": total_hubs,
        "predefined_cities": predefined_cities,
        "dynamic_cities": dynamic_cities,
        "total_cities": predefined_cities + dynamic_cities,
        "predefined_routes": len(route_map),
        "dynamic_direct_routes": direct_route_count,
        "multi_hop_routes": multihop_route_count,
        "total_routes": total_routes,
        "avg_routes_per_city": total_routes / (predefined_cities + dynamic_cities) if (predefined_cities + dynamic_cities) > 0 else 0
    }


def print_network_summary():
    """Print a formatted network summary"""
    summary = get_network_summary()
    
    print("\n" + "="*60)
    print("DYNAMIC NETWORK SUMMARY - NO HARDCODING")
    print("="*60)
    print(f"Network Type:           {summary['network_type']}")
    print(f"Warehouses:             {summary['warehouses']}")
    print(f"Distribution Hubs:      {summary['distribution_hubs']}")
    print(f"Cities Supported:       {summary['total_cities']} ({summary['predefined_cities']} predefined + {summary['dynamic_cities']} dynamic)")
    print(f"Total Routes:           {summary['total_routes']}")
    print(f"  - Predefined:         {summary['predefined_routes']}")
    print(f"  - Dynamic Direct:     {summary['dynamic_direct_routes']}")
    print(f"  - Multi-Hop:          {summary['multi_hop_routes']}")
    print(f"Avg Routes per City:    {summary['avg_routes_per_city']:.1f}")
    print("="*60 + "\n")
