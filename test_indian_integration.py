"""
Integration test: Test Guardian Mode with Indian cities
"""

from mitigation_module import solve_guardian_plan
from mitigation_module.input_handler import USD_TO_INR_RATE

def test_indian_city_integration():
    """Test full Guardian Mode workflow with Indian city"""
    print("=" * 80)
    print("INTEGRATION TEST: Indian City with Guardian Mode")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Mumbai with INR budget",
            "input": "Ship 500 units to Mumbai with budget ₹50,000",
            "expected_currency": "INR"
        },
        {
            "name": "Bangalore with USD budget (should convert)",
            "input": "Send 750 units to Bangalore with budget $5,000",
            "expected_currency": "INR",
            "expected_budget": 5000.0 * USD_TO_INR_RATE
        },
        {
            "name": "Delhi with Rs budget",
            "input": "Ship 1000 units to Delhi with Rs 100000 budget",
            "expected_currency": "INR"
        },
        {
            "name": "Boston with USD (unchanged)",
            "input": "Ship 500 units to Boston with budget $10,000",
            "expected_currency": "USD"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test['name']}")
        print(f"Input: {test['input']}")
        print(f"{'='*80}")
        
        try:
            initial_plan, mitigation_plan, risk_info, destination, requirements = solve_guardian_plan(test['input'])
            
            print(f"\n✅ Guardian Mode executed successfully")
            print(f"\n📋 Parsed Requirements:")
            print(f"   Destination: {requirements.get('destination')}")
            print(f"   Quantity: {requirements.get('quantity')}")
            print(f"   Budget: {requirements.get('budget')}")
            print(f"   Currency: {requirements.get('currency')}")
            print(f"   Is Indian City: {requirements.get('is_indian_city')}")
            
            # Verify currency
            if requirements.get('currency') == test['expected_currency']:
                print(f"\n✅ Currency correct: {requirements.get('currency')}")
            else:
                print(f"\n❌ Currency mismatch: got {requirements.get('currency')}, expected {test['expected_currency']}")
            
            # Verify budget conversion if applicable
            if 'expected_budget' in test:
                if abs(requirements.get('budget', 0) - test['expected_budget']) < 1.0:
                    print(f"✅ Budget conversion correct: {requirements.get('budget'):,.2f}")
                else:
                    print(f"❌ Budget conversion issue: got {requirements.get('budget')}, expected {test['expected_budget']}")
            
            # Show risk info
            print(f"\n🗞️ Risk Info:")
            print(f"   {risk_info}")
            
            # Show initial plan summary
            if initial_plan:
                print(f"\n📊 Initial Plan:")
                for route_id, qty in initial_plan.items():
                    print(f"   Route {route_id}: {qty} units")
            
            # Show mitigation plan summary
            if mitigation_plan:
                print(f"\n🛡️ Mitigation Plan:")
                for route_id, qty in mitigation_plan.items():
                    print(f"   Route {route_id}: {qty} units")
            
            print(f"\n✅ TEST PASSED")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED with error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n🇮🇳 INTEGRATION TEST: Guardian Mode with Indian Cities 🇮🇳\n")
    test_indian_city_integration()
    print("\n" + "=" * 80)
    print("TESTING COMPLETE!")
    print("=" * 80)
