"""
Test the new input parsing capabilities
"""
from mitigation_module.input_handler import extract_shipment_requirements

print("\n" + "="*60)
print("TESTING INPUT PARSING - COMPREHENSIVE REQUIREMENTS")
print("="*60)

# Test Case 1: Full requirements
test1 = "I need to ship 500 units to Boston on Feb 10th with budget $15000"
print(f"\n📝 Input: {test1}")
reqs1 = extract_shipment_requirements(test1)
print(f"\n✅ PARSED:")
print(f"  🎯 Destination: {reqs1['destination']}")
print(f"  📦 Quantity: {reqs1['quantity']} units" if reqs1['quantity'] else "  📦 Quantity: Not specified")
print(f"  💵 Budget: ${reqs1['budget']:,.2f}" if reqs1['budget'] else "  💵 Budget: Not specified")
print(f"  📅 Date: {reqs1['date']}" if reqs1['date'] else "  📅 Date: Not specified")
print(f"  ⚡ Priority: {reqs1['priority']}" if reqs1['priority'] else "  ⚡ Priority: Not specified")

# Test Case 2: with priority
test2 = "URGENT: Ship 1000 units to Chicago by 2/15"
print(f"\n\n📝 Input: {test2}")
reqs2 = extract_shipment_requirements(test2)
print(f"\n✅ PARSED:")
print(f"  🎯 Destination: {reqs2['destination']}")
print(f"  📦 Quantity: {reqs2['quantity']} units" if reqs2['quantity'] else "  📦 Quantity: Not specified")
print(f"  💵 Budget: ${reqs2['budget']:,.2f}" if reqs2['budget'] else "  💵 Budget: Not specified")
print(f"  📅 Date: {reqs2['date']}" if reqs2['date'] else "  📅 Date: Not specified")
print(f"  ⚡ Priority: {reqs2['priority']}" if reqs2['priority'] else "  ⚡ Priority: Not specified")

# Test Case 3: Minimal (only city)
test3 = "Ship to Miami"
print(f"\n\n📝 Input: {test3}")
reqs3 = extract_shipment_requirements(test3)
print(f"\n✅ PARSED:")
print(f"  🎯 Destination: {reqs3['destination']}")
print(f"  📦 Quantity: {reqs3['quantity']} units" if reqs3['quantity'] else "  📦 Quantity: Not specified (will use default)")
print(f"  💵 Budget: ${reqs3['budget']:,.2f}" if reqs3['budget'] else "  💵 Budget: Not specified")
print(f"  📅 Date: {reqs3['date']}" if reqs3['date'] else "  📅 Date: Not specified")
print(f"  ⚡ Priority: {reqs3['priority']}" if reqs3['priority'] else "  ⚡ Priority: Not specified")

# Test Case 4: New city with quantity
test4 = "Need expedited delivery of 750 units to Seattle with max cost $20,000"
print(f"\n\n📝 Input: {test4}")
reqs4 = extract_shipment_requirements(test4)
print(f"\n✅ PARSED:")
print(f"  🎯 Destination: {reqs4['destination']}")
print(f"  📦 Quantity: {reqs4['quantity']} units" if reqs4['quantity'] else "  📦 Quantity: Not specified")
print(f"  💵 Budget: ${reqs4['budget']:,.2f}" if reqs4['budget'] else "  💵 Budget: Not specified")
print(f"  📅 Date: {reqs4['date']}" if reqs4['date'] else "  📅 Date: Not specified")
print(f"  ⚡ Priority: {reqs4['priority']}" if reqs4['priority'] else "  ⚡ Priority: Not specified")

print("\n" + "="*60)
print("✅ INPUT PARSING TEST COMPLETE")
print("="*60 + "\n")
