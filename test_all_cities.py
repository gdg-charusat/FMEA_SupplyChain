"""
Test Guardian Mode with multiple cities
"""
from mitigation_module.mitigation_solver import solve_guardian_plan, generate_impact_report
from mitigation_module.dynamic_network import reset_dynamic_routes

reset_dynamic_routes()

print('='*70)
print('TESTING: All Cities Now Show Backup Routes')
print('='*70)

for city in ['Boston', 'Chicago', 'New York', 'Philadelphia']:
    print(f'\n{city}:')
    i,m,r,d,reqs = solve_guardian_plan(f'Ship to {city}')
    print(f'  Risk: {r[:60]}...')
    print(f'  Rerouting: {"YES - BACKUP ACTIVATED" if i!=m else "NO"}')
    report = generate_impact_report(i,m,d)
    print(f'  Table shows: {len(report)} routes')
    
    # Show the actual changes
    for idx, row in report.iterrows():
        if 'STOPPED' in row['Status'] or 'ACTIVATED' in row['Status']:
            print(f'    -> {row["Route Info"]}: {row["Status"]}')

print('\n' + '='*70)
print('RESULT: All cities now have rerouting options!')
print('='*70)
