"""
Test script for Indian city detection and currency conversion
"""

from mitigation_module.input_handler import (
    extract_shipment_requirements,
    is_indian_city,
    extract_budget,
    USD_TO_INR_RATE
)

def test_indian_cities():
    """Test Indian city detection"""
    print("=" * 80)
    print("TEST 1: Indian City Detection")
    print("=" * 80)
    
    test_cities = [
        ("Mumbai", True),
        ("Delhi", True),
        ("Bangalore", True),
        ("Chennai", True),
        ("Boston", False),
        ("Chicago", False),
        (None, False)
    ]
    
    for city, expected in test_cities:
        result = is_indian_city(city)
        status = "✅" if result == expected else "❌"
        print(f"{status} {city}: {result} (expected {expected})")
    print()

def test_currency_extraction():
    """Test budget extraction with different currencies"""
    print("=" * 80)
    print("TEST 2: Currency Extraction")
    print("=" * 80)
    
    test_cases = [
        # USD cases
        ("Budget of $10,000", {'amount': 10000.0, 'currency': 'USD'}),
        ("I have $5000 budget", {'amount': 5000.0, 'currency': 'USD'}),
        ("max cost 15000", {'amount': 15000.0, 'currency': 'USD'}),
        
        # INR cases
        ("Budget of ₹50,000", {'amount': 50000.0, 'currency': 'INR'}),
        ("Rs 100000 budget", {'amount': 100000.0, 'currency': 'INR'}),
        ("I have rupees 75000", {'amount': 75000.0, 'currency': 'INR'}),
        ("INR 200000", {'amount': 200000.0, 'currency': 'INR'}),
    ]
    
    for text, expected in test_cases:
        result = extract_budget(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: '{text}'")
        print(f"   Result: {result}")
        print(f"   Expected: {expected}")
        print()

def test_full_requirements():
    """Test complete requirement extraction"""
    print("=" * 80)
    print("TEST 3: Full Requirements Extraction")
    print("=" * 80)
    
    test_cases = [
        {
            "input": "Ship 500 units to Mumbai with budget ₹50,000",
            "expected": {
                "destination": "Mumbai",
                "quantity": 500,
                "budget": 50000.0,
                "currency": "INR",
                "is_indian_city": True
            }
        },
        {
            "input": "Send 1000 units to Delhi with Rs 100000 budget",
            "expected": {
                "destination": "Delhi",
                "quantity": 1000,
                "budget": 100000.0,
                "currency": "INR",
                "is_indian_city": True
            }
        },
        {
            "input": "Ship 750 units to Bangalore with budget $5,000",
            "expected": {
                "destination": "Bangalore",
                "quantity": 750,
                "budget": 5000.0 * USD_TO_INR_RATE,  # Should auto-convert
                "currency": "INR",
                "is_indian_city": True
            }
        },
        {
            "input": "Ship 500 units to Boston with budget $10,000",
            "expected": {
                "destination": "Boston",
                "quantity": 500,
                "budget": 10000.0,
                "currency": "USD",
                "is_indian_city": False
            }
        },
        {
            "input": "I need to ship 300 units to Chennai",
            "expected": {
                "destination": "Chennai",
                "quantity": 300,
                "budget": None,
                "currency": "INR",  # Auto-detect based on city
                "is_indian_city": True
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test['input']}")
        print("-" * 80)
        result = extract_shipment_requirements(test['input'])
        
        checks = {
            "destination": result['destination'] == test['expected']['destination'],
            "quantity": result['quantity'] == test['expected']['quantity'],
            "currency": result['currency'] == test['expected']['currency'],
            "is_indian_city": result['is_indian_city'] == test['expected']['is_indian_city'],
        }
        
        # Check budget (may be None)
        if test['expected']['budget'] is not None:
            checks['budget'] = abs(result['budget'] - test['expected']['budget']) < 0.01 if result['budget'] else False
        else:
            checks['budget'] = result['budget'] is None
        
        print(f"   Destination: {'✅' if checks['destination'] else '❌'} {result['destination']} (expected {test['expected']['destination']})")
        print(f"   Quantity: {'✅' if checks['quantity'] else '❌'} {result['quantity']} (expected {test['expected']['quantity']})")
        print(f"   Budget: {'✅' if checks['budget'] else '❌'} {result['budget']} (expected {test['expected']['budget']})")
        print(f"   Currency: {'✅' if checks['currency'] else '❌'} {result['currency']} (expected {test['expected']['currency']})")
        print(f"   Is Indian: {'✅' if checks['is_indian_city'] else '❌'} {result['is_indian_city']} (expected {test['expected']['is_indian_city']})")
        
        if all(checks.values()):
            print("   ✅ PASSED")
        else:
            print("   ❌ FAILED")

def test_currency_conversion():
    """Test USD to INR auto-conversion for Indian cities"""
    print("\n" + "=" * 80)
    print("TEST 4: Auto Currency Conversion")
    print("=" * 80)
    
    # When user specifies USD budget for Indian city, it should convert to INR
    result = extract_shipment_requirements("Ship 500 units to Mumbai with budget $1,000")
    
    expected_inr = 1000.0 * USD_TO_INR_RATE
    
    print(f"\nInput: 'Ship 500 units to Mumbai with budget $1,000'")
    print(f"Expected: Budget converted to ₹{expected_inr:,.2f}")
    print(f"Result: Budget = {result['budget']}, Currency = {result['currency']}")
    
    if result['currency'] == 'INR' and abs(result['budget'] - expected_inr) < 0.01:
        print("✅ PASSED: USD budget correctly converted to INR for Indian city")
    else:
        print("❌ FAILED: Currency conversion issue")

if __name__ == "__main__":
    print("\n🇮🇳 TESTING INDIAN CITY AND CURRENCY SUPPORT 🇮🇳\n")
    
    test_indian_cities()
    test_currency_extraction()
    test_full_requirements()
    test_currency_conversion()
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE!")
    print("=" * 80)
