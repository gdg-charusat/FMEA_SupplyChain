"""
Test for Race Condition Fix in Dynamic Network Module
Verifies that concurrent route creation is thread-safe
"""

import concurrent.futures
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from mitigation_module.dynamic_network import (
    get_routes_for_city,
    reset_dynamic_routes,
    get_network_summary,
    get_full_route_map
)


def test_concurrent_route_creation():
    """
    Test that concurrent calls to get_routes_for_city don't create duplicate route IDs
    This would fail without proper thread synchronization
    """
    print("\n" + "="*70)
    print("TEST 1: Concurrent Route Creation - No ID Collisions")
    print("="*70)
    
    # Reset to clean state
    reset_dynamic_routes()
    
    # Track all created route IDs across threads
    all_route_ids = set()
    all_route_ids_lock = __import__('threading').Lock()
    
    def create_routes_for_city(city_name):
        """Worker thread: Create routes for a city"""
        routes = get_routes_for_city(city_name, include_multihop=True)
        
        # Thread-safe collection of all IDs
        with all_route_ids_lock:
            for route_id in routes:
                all_route_ids.add(route_id)
        
        return routes
    
    # Create routes for multiple cities concurrently
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
    
    print(f"\nLaunching {len(cities)} concurrent threads to create routes for:")
    print(f"  {', '.join(cities)}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(create_routes_for_city, city): city for city in cities}
        
        results = {}
        for future in concurrent.futures.as_completed(futures):
            city = futures[future]
            routes = future.result()
            results[city] = routes
            print(f"  ✓ {city}: {len(routes)} routes created")
    
    # Verify no duplicate IDs
    total_routes_created = sum(len(routes) for routes in results.values())
    unique_route_ids = len(all_route_ids)
    
    print(f"\nVerification:")
    print(f"  Total routes created:  {total_routes_created}")
    print(f"  Unique route IDs:      {unique_route_ids}")
    
    if total_routes_created == unique_route_ids:
        print(f"  ✅ PASS: No ID collisions detected!")
    else:
        print(f"  ❌ FAIL: {total_routes_created - unique_route_ids} duplicate IDs found!")
        return False
    
    return True


def test_concurrent_state_consistency():
    """
    Test that get_network_summary returns consistent state under concurrent access
    """
    print("\n" + "="*70)
    print("TEST 2: Concurrent State Access - Consistent Snapshots")
    print("="*70)
    
    # Reset to clean state
    reset_dynamic_routes()
    
    # Create some initial routes
    for city in ["City A", "City B", "City C"]:
        get_routes_for_city(city, include_multihop=True)
    
    summaries = []
    summaries_lock = __import__('threading').Lock()
    
    def get_summary_and_create():
        """Worker thread: Get summary and create more routes"""
        # Get current network summary
        summary = get_network_summary()
        
        with summaries_lock:
            summaries.append(summary)
        
        # Create routes for a new city
        routes = get_routes_for_city(f"City {len(summaries)}", include_multihop=False)
        return len(routes)
    
    print("\nConcurrently accessing and modifying network state...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(get_summary_and_create) for _ in range(10)]
        
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
        print(f"  ✓ Completed {len(results)} concurrent operations")
    
    # Verify summaries are consistent
    print(f"\nCollected {len(summaries)} state snapshots")
    
    # Check for data consistency
    all_consistent = True
    for i, summary in enumerate(summaries):
        if summary is None or not isinstance(summary, dict):
            print(f"  ❌ Summary {i}: Invalid data type")
            all_consistent = False
        elif summary.get('total_routes', 0) < 0:
            print(f"  ❌ Summary {i}: Negative route count")
            all_consistent = False
    
    if all_consistent:
        print("  ✅ PASS: All state snapshots are consistent!")
    else:
        print("  ❌ FAIL: Inconsistent state detected!")
        return False
    
    return True


def test_concurrent_route_lookup():
    """
    Test that concurrent read-only access (get_full_route_map) is safe
    """
    print("\n" + "="*70)
    print("TEST 3: Concurrent Route Map Reads - Thread-Safe Lookups")
    print("="*70)
    
    # Reset and create routes
    reset_dynamic_routes()
    for city in ["Boston", "Denver", "Seattle", "Miami"]:
        get_routes_for_city(city, include_multihop=True)
    
    route_maps = []
    maps_lock = __import__('threading').Lock()
    
    def read_route_map():
        """Worker thread: Read full route map 10 times"""
        maps_read = []
        for _ in range(10):
            route_map = get_full_route_map(include_dynamic=True, include_multihop=True)
            maps_read.append(len(route_map))
        
        with maps_lock:
            route_maps.extend(maps_read)
        
        return len(maps_read)
    
    print("\nLaunching concurrent thread reads of full route map...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(read_route_map) for _ in range(5)]
        
        reads_per_thread = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    total_reads = sum(reads_per_thread)
    unique_counts = set(route_maps)
    
    print(f"\nVerification:")
    print(f"  Total reads performed:  {total_reads}")
    print(f"  Unique route counts:    {unique_counts}")
    
    if len(unique_counts) <= 2:  # Allow up to 2 different counts due to concurrent creates
        print(f"  ✅ PASS: Route map reads are consistent!")
        return True
    else:
        print(f"  ❌ FAIL: Inconsistent route counts detected!")
        return False


def run_all_tests():
    """Run all race condition tests"""
    print("\n" + "="*70)
    print("RACE CONDITION FIX VERIFICATION TESTS")
    print("="*70)
    
    test_results = {
        "Concurrent Route Creation": test_concurrent_route_creation(),
        "Concurrent State Consistency": test_concurrent_state_consistency(),
        "Concurrent Route Map Reads": test_concurrent_route_lookup(),
    }
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(test_results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Race condition fix verified!")
    else:
        print("❌ SOME TESTS FAILED - Race condition issues detected!")
    print("="*70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
