from mitigation_module.risk_monitor import scan_news_for_risk

cities = ['Boston', 'Chicago', 'New York', 'Philadelphia', 'Miami', 'Dallas', 'Seattle', 'Bangalore', 'Chennai', 'Pune', 'Jaipur']

print('='*70)
print('CITY RISK SUMMARY')
print('='*70)

for city in cities:
    risk = scan_news_for_risk(city)
    if risk:
        print(f'{city:15} -> {risk["reason"]:45} ({risk["multiplier"]}x)')
    else:
        print(f'{city:15} -> No risks found')

print('='*70)
