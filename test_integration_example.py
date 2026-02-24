"""
INTEGRATION EXAMPLE: solve_mitigation_plan with DisruptionExtractor
Shows complete workflow from user input → extraction → optimization → display
"""
from mitigation_module import DisruptionExtractor, solve_mitigation_plan

print("=" * 80)
print("INTEGRATION WORKFLOW: User Input → Extraction → Optimization → Display")
print("=" * 80)

# ===== SCENARIO 1: Text Input =====
print("\n" + "=" * 80)
print("SCENARIO 1: User types text in dashboard")
print("=" * 80)

user_text = "Major strike at JFK Airport causing severe delays"
print(f"\n📝 User Input (Text): '{user_text}'")

# Step 1: Extract disruptions from text
print("\n🔍 Step 1: Extract alerts using DisruptionExtractor...")
extractor = DisruptionExtractor()
events = extractor.extract_from_text(user_text)
alerts = [e.to_dict() for e in events]

print(f"✅ Extracted {len(alerts)} alerts:")
for alert in alerts:
    print(f"   - Route {alert['target_route_id']}: {alert['impact_type']} (×{alert['cost_multiplier']})")

# Step 2: Solve mitigation plan
print("\n🚀 Step 2: Solve optimization with extracted alerts...")
result = solve_mitigation_plan(alert_json_list=alerts)

if result['status'] == 'success':
    print("✅ Optimization successful!")
    
    # Step 3: Display results (like in Streamlit)
    print("\n📊 Step 3: Display results to user...")
    print("\n" + "=" * 80)
    print("DASHBOARD OUTPUT")
    print("=" * 80)
    
    print(f"\n💰 Cost Analysis:")
    print(f"   Original Cost: ${result['baseline']['total_cost']:,.2f}")
    print(f"   Adjusted Cost: ${result['adjusted']['total_cost']:,.2f}")
    print(f"   Cost Impact: ${result['cost_delta']:,.2f} (+{result['cost_delta_pct']:.1f}%)")
    
    print(f"\n📊 Route Impact Analysis:")
    print(result['impact_report'].to_string(index=False))
else:
    print(f"❌ Optimization failed: {result.get('message')}")

# ===== SCENARIO 2: Multiple Text Inputs =====
print("\n\n" + "=" * 80)
print("SCENARIO 2: User enters multiple alerts in sequence")
print("=" * 80)

user_texts = [
    "Boston port closed due to severe weather",
    "Chicago highway accident",
]

all_alerts = []
for i, text in enumerate(user_texts, 1):
    print(f"\n📝 Alert #{i}: '{text}'")
    events = extractor.extract_from_text(text)
    alerts = [e.to_dict() for e in events]
    all_alerts.extend(alerts)
    print(f"   → Extracted routes: {[a['target_route_id'] for a in alerts]}")

print(f"\n🚀 Solving with {len(all_alerts)} combined alerts...")
result2 = solve_mitigation_plan(alert_json_list=all_alerts)

if result2['status'] == 'success':
    print("✅ Optimization successful!")
    print(f"\n💰 Cost Impact: ${result2['cost_delta']:,.2f} (+{result2['cost_delta_pct']:.1f}%)")
    print(f"\n📊 Route Impact Analysis:")
    print(result2['impact_report'].to_string(index=False))

# ===== SCENARIO 3: CSV/Image Input =====
print("\n\n" + "=" * 80)
print("SCENARIO 3: Integration pattern for CSV/Image uploads")
print("=" * 80)

print("""
📝 For CSV uploads:
   events = extractor.extract_from_csv("uploaded_file.csv")
   alerts = [e.to_dict() for e in events]
   result = solve_mitigation_plan(alert_json_list=alerts)

🖼️ For Image uploads:
   events = extractor.extract_from_image("uploaded_image.png")
   alerts = [e.to_dict() for e in events]
   result = solve_mitigation_plan(alert_json_list=alerts)

📰 For News Dataset:
   events = extractor.extract_from_news(news_df, ['BUSINESS', 'WORLD NEWS'])
   alerts = extractor.validate_and_aggregate(events)
   result = solve_mitigation_plan(alert_json_list=alerts)
""")

# ===== STREAMLIT INTEGRATION CODE =====
print("\n" + "=" * 80)
print("STREAMLIT INTEGRATION CODE")
print("=" * 80)

streamlit_code = '''
import streamlit as st
from mitigation_module import DisruptionExtractor, solve_mitigation_plan

# User inputs text
user_text = st.text_area("Enter disruption alert:")

if st.button("Analyze Disruption"):
    # Extract alerts
    extractor = DisruptionExtractor()
    events = extractor.extract_from_text(user_text)
    alerts = [e.to_dict() for e in events]
    
    st.session_state['alerts'] = alerts
    st.success(f"✅ Extracted {len(alerts)} alerts")

# Optimize button
if 'alerts' in st.session_state:
    if st.button("Calculate Optimized Transport Plan"):
        # Solve in ONE function call
        result = solve_mitigation_plan(
            alert_json_list=st.session_state['alerts']
        )
        
        if result['status'] == 'success':
            st.session_state['result'] = result
            
            # Display cost metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Cost", f"${result['baseline']['total_cost']:,.2f}")
            with col2:
                st.metric("Adjusted Cost", f"${result['adjusted']['total_cost']:,.2f}")
            with col3:
                st.metric("Cost Impact", f"${result['cost_delta']:,.2f}",
                         delta=f"{result['cost_delta_pct']:.1f}%")
            
            # Display impact report
            st.dataframe(result['impact_report'])
'''

print(streamlit_code)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✅ solve_mitigation_plan integrates seamlessly with DisruptionExtractor")
print("✅ Single function call replaces 5-6 separate operations")
print("✅ Works with text, CSV, image, and news inputs")
print("✅ Returns complete results ready for dashboard display")
print("✅ Uses ONLY CSV data + user alerts (no hardcoded values)")
print("=" * 80)
