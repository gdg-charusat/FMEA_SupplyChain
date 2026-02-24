"""
TEST: Verify hardcoded fallback is removed and errors are properly raised
"""
from mitigation_module import DisruptionExtractor
import sys

print("=" * 80)
print("TEST: Hardcoded Fallback Removal Verification")
print("=" * 80)

extractor = DisruptionExtractor()

# ===== TEST 1: Valid input (should work) =====
print("\n" + "=" * 80)
print("TEST 1: Valid Input - 'JFK Strike'")
print("=" * 80)

try:
    text1 = "Strike at JFK Airport"
    events1 = extractor.extract_from_text(text1)
    print(f"✅ SUCCESS: Extracted {len(events1)} events")
    for e in events1:
        print(f"   - Route {e.target_route_id}: {e.impact_type} (×{e.cost_multiplier})")
except Exception as e:
    print(f"❌ FAILED: {e}")

# ===== TEST 2: Invalid input (should raise error, NOT return [1,5]) =====
print("\n" + "=" * 80)
print("TEST 2: Invalid Input - 'Toxic Spill' (no location keyword)")
print("=" * 80)

try:
    text2 = "Toxic Spill"
    events2 = extractor.extract_from_text(text2)
    
    # If we get here, check if it's the old hardcoded [1, 5]
    route_ids = [e.target_route_id for e in events2]
    if route_ids == [1, 5]:
        print(f"❌ FAILED: Still using hardcoded fallback [1, 5]!")
        print(f"   Got routes: {route_ids}")
        sys.exit(1)
    else:
        print(f"⚠️  WARNING: Got routes {route_ids}, but expected an error")
        print(f"   This means a new fallback might be in place")
        
except ValueError as e:
    print(f"✅ SUCCESS: Properly raised ValueError as expected")
    print(f"   Error message: {str(e)[:200]}...")
except Exception as e:
    print(f"⚠️  Got different error type: {type(e).__name__}: {e}")

# ===== TEST 3: Another invalid input =====
print("\n" + "=" * 80)
print("TEST 3: Invalid Input - 'Random text with no keywords'")
print("=" * 80)

try:
    text3 = "Some random text with no location keywords at all"
    events3 = extractor.extract_from_text(text3)
    
    route_ids = [e.target_route_id for e in events3]
    print(f"❌ FAILED: Should have raised error but got routes: {route_ids}")
    
except ValueError as e:
    print(f"✅ SUCCESS: Properly raised ValueError")
    print(f"   Error message snippet: {str(e)[:150]}...")
except Exception as e:
    print(f"⚠️  Got different error: {type(e).__name__}: {e}")

# ===== TEST 4: Valid input with different location =====
print("\n" + "=" * 80)
print("TEST 4: Valid Input - 'Boston Port Closure'")
print("=" * 80)

try:
    text4 = "Boston port closure due to weather"
    events4 = extractor.extract_from_text(text4)
    route_ids = [e.target_route_id for e in events4]
    print(f"✅ SUCCESS: Extracted {len(events4)} events for routes {route_ids}")
    
    # Verify it's NOT [1, 5] (the old fallback)
    if route_ids == [1, 5]:
        print(f"⚠️  WARNING: Got [1, 5] which was the old hardcoded fallback")
        print(f"   But Boston should map to [1, 4], so this might be coincidence")
    
except Exception as e:
    print(f"❌ FAILED: Valid input should not raise error: {e}")

# ===== SUMMARY =====
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✅ Valid inputs (JFK, Boston) should extract routes successfully")
print("❌ Invalid inputs (Toxic Spill, random text) should RAISE ValueError")
print("🚫 System should NEVER return hardcoded [1, 5] fallback")
print("=" * 80)
