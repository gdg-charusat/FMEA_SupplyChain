# mitigation_module/network_config.py
"""
DYNAMIC NETWORK CONFIGURATION - NO HARDCODING
All routes are generated dynamically based on warehouse and hub configuration
"""

import os
import yaml

# Get the path to the config file
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_BASE_DIR, 'config', 'network.yaml')

# Load the configuration once
try:
    with open(_CONFIG_PATH, 'r') as f:
        _config = yaml.safe_load(f) or {}
except (yaml.YAMLError, IOError) as e:
    print(f"CRITICAL ERROR: Failed to load network configuration from {_CONFIG_PATH}")
    print(f"Error details: {e}")
    _config = {}

# =========================================
# DYNAMIC WAREHOUSE CONFIGURATION
# =========================================
WAREHOUSES = _config.get('warehouses', {})

# =========================================
# INTERMEDIATE DISTRIBUTION HUBS
# =========================================
DISTRIBUTION_HUBS = _config.get('distribution_hubs', {})

# =========================================
# PREDEFINED CITIES (Legacy Support)
# =========================================
DEMAND_REQ = _config.get('demand_req', {})

# =========================================
# DYNAMIC ROUTE GENERATION
# =========================================
# Legacy route_map for backward compatibility (Routes 1-10)
route_map = {}
for k, v in _config.get('route_map', {}).items():
    route_map[int(k)] = tuple(v)

# Primary routes (for risk application logic)
PRIMARY_ROUTES = {1, 2, 3, 5, 9, 10}

# Dynamic routes start from ID 100
DYNAMIC_ROUTE_START_ID = 100

# Multi-hop routes start from ID 1000
MULTIHOP_ROUTE_START_ID = 1000

# Backward compatibility
ROUTE_MAP = route_map
SUPPLY_CAPACITY = {name: info["capacity"] for name, info in WAREHOUSES.items()}
SOURCES = list(WAREHOUSES.keys())
DESTINATIONS = list(DEMAND_REQ.keys())

def get_total_warehouse_capacity():
    """Calculate total capacity across all warehouses"""
    return sum(info["capacity"] for info in WAREHOUSES.values())

def get_warehouse_list():
    """Get list of all warehouse names sorted by priority"""
    return sorted(WAREHOUSES.keys(), key=lambda x: WAREHOUSES[x]["priority"])

def get_hub_list():
    """Get list of all distribution hub names"""
    return list(DISTRIBUTION_HUBS.keys())

def validate_network():
    """Validate network configuration including dynamic routes"""
    from mitigation_module.dynamic_network import get_full_route_map
    
    total_supply = get_total_warehouse_capacity()
    total_demand = sum(DEMAND_REQ.values())
    
    # Get full route map including dynamic routes
    full_map = get_full_route_map(include_dynamic=True, include_multihop=True)
    
    # Count route types
    direct_routes = sum(1 for route in full_map.values() if len(route) == 2)
    multihop_routes = sum(1 for route in full_map.values() if len(route) == 3)
    
    return {
        "total_supply": total_supply,
        "total_demand": total_demand,
        "surplus": total_supply - total_demand,
        "num_routes": len(route_map),
        "num_total_routes": len(full_map),
        "num_direct_routes": direct_routes,
        "num_multihop_routes": multihop_routes,
        "num_warehouses": len(WAREHOUSES),
        "num_hubs": len(DISTRIBUTION_HUBS),
        "num_clients": len(DEMAND_REQ),
        "dynamic_routing": "ENABLED"
    }
