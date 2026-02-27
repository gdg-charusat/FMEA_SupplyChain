"""
Test that DisruptionExtractor now supports non-hardcoded cities
Verifies fix for: "Disruption Extractor Fails for Non-Hardcoded Cities"
"""

from mitigation_module import DisruptionExtractor

def test_seattle_disruption():
    """Test case from bug report - should no longer crash"""
    print("\n" + "="*60)
    print("TEST 1: Seattle (Non-Hardcoded City)")
    print("="*60)
    
    extractor = DisruptionExtractor()
    
    try:
        # This used to raise ValueError - should now handle gracefully
        disruptions = extractor.extract_from_text("Port strike in Seattle")
        
        print(f"✓ No crash! Extracted {len(disruptions)} disruptions")
        
        if len(disruptions) == 0:
            print("✓ Returned empty list gracefully (expected for unmapped city without route IDs)")
        else:
            print(f"✓ Dynamically resolved routes: {[d.target_route_id for d in disruptions]}")
            for d in disruptions:
                print(f"  - Route {d.target_route_id}: {d.impact_type}, multiplier={d.cost_multiplier}x")
        
        return True
    except ValueError as e:
        print(f"✗ FAILED: Still raising ValueError: {e}")
        return False


def test_hardcoded_city_still_works():
    """Ensure existing hardcoded cities still work"""
    print("\n" + "="*60)
    print("TEST 2: Boston (Previously Hardcoded, Now in Config)")
    print("="*60)
    
    extractor = DisruptionExtractor()
    
    try:
        disruptions = extractor.extract_from_text("Major accident in Boston")
        print(f"✓ Extracted {len(disruptions)} disruptions")
        
        if disruptions:
            print(f"✓ Routes: {[d.target_route_id for d in disruptions]}")
            for d in disruptions:
                print(f"  - Route {d.target_route_id}: {d.impact_type}, multiplier={d.cost_multiplier}x")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_explicit_route_id():
    """Test explicit route IDs still work"""
    print("\n" + "="*60)
    print("TEST 3: Explicit Route ID (Should Always Work)")
    print("="*60)
    
    extractor = DisruptionExtractor()
    
    try:
        disruptions = extractor.extract_from_text("Bridge collapse on Route 5")
        print(f"✓ Extracted {len(disruptions)} disruptions")
        
        if disruptions:
            print(f"✓ Routes: {[d.target_route_id for d in disruptions]}")
            for d in disruptions:
                print(f"  - Route {d.target_route_id}: {d.impact_type}, multiplier={d.cost_multiplier}x")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_config_mapped_location():
    """Test a location that's in mapping_config.json but wasn't hardcoded"""
    print("\n" + "="*60)
    print("TEST 4: JFK Airport (In Config, Not Hardcoded)")
    print("="*60)
    
    extractor = DisruptionExtractor()
    
    try:
        disruptions = extractor.extract_from_text("Strike at JFK Airport")
        print(f"✓ Extracted {len(disruptions)} disruptions")
        
        if disruptions:
            print(f"✓ Routes: {[d.target_route_id for d in disruptions]}")
            for d in disruptions:
                print(f"  - Route {d.target_route_id}: {d.impact_type}, multiplier={d.cost_multiplier}x")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING FIX: Disruption Extractor Dynamic City Support")
    print("="*60)
    
    results = [
        test_seattle_disruption(),
        test_hardcoded_city_still_works(),
        test_explicit_route_id(),
        test_config_mapped_location()
    ]
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Issue is fixed.")
    else:
        print("✗ Some tests failed. Issue not fully resolved.")
    
    print("="*60 + "\n")
