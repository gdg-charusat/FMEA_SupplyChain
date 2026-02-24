"""
Quick Start Script - Process YOUR Data
Works with your FMEA.csv and archive (3) car reviews
"""

import sys
from pathlib import Path
import yaml
import pandas as pd

sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator
from utils import setup_logging, generate_summary_report

setup_logging('INFO')

print("=" * 70)
print("  🚀 FMEA GENERATOR - WORKING WITH YOUR DATA")
print("=" * 70)

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# For faster processing, use rule-based extraction
# (Set to None to use LLM models)
config['model']['name'] = None

# Initialize generator
print("\n📦 Initializing FMEA Generator...")
generator = FMEAGenerator(config)

# Create output directory
Path('output').mkdir(exist_ok=True)

print("\n" + "=" * 70)
print("  OPTION 1: Process Structured Data (FMEA.csv)")
print("=" * 70)

try:
    print("\n📊 Loading FMEA.csv...")
    
    # Read existing FMEA.csv to understand structure
    existing_fmea = pd.read_csv('FMEA.csv')
    print(f"✓ Found {len(existing_fmea)} existing failure modes")
    print(f"✓ Columns: {', '.join(existing_fmea.columns[:5])}...")
    
    # The FMEA.csv already has scores, so we'll validate and enhance it
    print("\n🔄 Processing structured FMEA data...")
    fmea_structured = generator.generate_from_structured('FMEA.csv')
    
    print(f"\n✅ Generated enhanced FMEA with {len(fmea_structured)} entries")
    
    # Show top risks
    print("\n🎯 TOP 5 RISKS FROM YOUR STRUCTURED DATA:")
    print("-" * 70)
    top_5 = fmea_structured.nlargest(5, 'Rpn')[['Failure Mode', 'Component', 'Rpn', 'Action Priority']]
    for idx, row in top_5.iterrows():
        print(f"{idx+1}. {row['Failure Mode']}")
        print(f"   Component: {row['Component']} | RPN: {row['Rpn']} | Priority: {row['Action Priority']}")
    
    # Export
    output_path = 'output/YOUR_STRUCTURED_FMEA.xlsx'
    generator.export_fmea(fmea_structured, output_path, format='excel')
    print(f"\n💾 Exported to: {output_path}")
    
except Exception as e:
    print(f"\n❌ Error processing FMEA.csv: {e}")

print("\n" + "=" * 70)
print("  OPTION 2: Process Car Reviews (archive (3))")
print("=" * 70)

# List available car brands
review_files = list(Path('archive (3)').glob('*.csv'))
print(f"\n📁 Found {len(review_files)} car review files")

# Let user choose or process popular brands
popular_brands = [
    'Scraped_Car_Review_ford.csv',
    'Scrapped_Car_Reviews_Toyota.csv',
    'Scrapped_Car_Reviews_Honda.csv',
    'Scrapped_Car_Reviews_BMW.csv',
    'Scraped_Car_Review_tesla.csv'
]

print("\n🚗 Processing sample car brands (Ford, Toyota, Honda)...")
print("   (This may take a few minutes for large datasets)")

for brand_file in popular_brands[:3]:  # Process first 3
    file_path = Path('archive (3)') / brand_file
    
    if not file_path.exists():
        continue
    
    brand_name = brand_file.replace('Scraped_Car_Review_', '').replace('Scrapped_Car_Reviews_', '').replace('.csv', '')
    
    print(f"\n📝 Processing {brand_name.upper()} reviews...")
    
    try:
        # Limit reviews for faster processing (increase for full analysis)
        config['text_processing']['max_reviews_per_batch'] = 100
        
        fmea_text = generator.generate_from_text(str(file_path), is_file=True)
        
        print(f"✅ Generated {len(fmea_text)} failure modes from {brand_name} reviews")
        
        # Show top critical issues
        critical = fmea_text[fmea_text['Action Priority'] == 'Critical']
        if len(critical) > 0:
            print(f"⚠️  Found {len(critical)} CRITICAL issues:")
            for idx, row in critical.head(3).iterrows():
                print(f"   - {row['Failure Mode'][:60]}...")
        
        # Export
        output_path = f'output/YOUR_{brand_name.upper()}_FMEA.xlsx'
        generator.export_fmea(fmea_text, output_path, format='excel')
        print(f"💾 Exported to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error processing {brand_name}: {e}")

print("\n" + "=" * 70)
print("  OPTION 3: Hybrid Analysis (Structured + Unstructured)")
print("=" * 70)

try:
    print("\n🔀 Combining FMEA.csv + Ford reviews...")
    
    # Limit reviews for demo
    config['text_processing']['max_reviews_per_batch'] = 50
    
    fmea_hybrid = generator.generate_hybrid(
        structured_file='FMEA.csv',
        text_input='archive (3)/Scraped_Car_Review_ford.csv'
    )
    
    print(f"\n✅ Generated hybrid FMEA with {len(fmea_hybrid)} total entries")
    
    # Show breakdown by source
    if 'Source' in fmea_hybrid.columns:
        source_counts = fmea_hybrid['Source'].value_counts()
        print("\n📊 Breakdown by source:")
        for source, count in source_counts.items():
            print(f"   {source}: {count} entries")
    
    # Show top 10 risks overall
    print("\n🎯 TOP 10 RISKS FROM HYBRID ANALYSIS:")
    print("-" * 70)
    top_10 = fmea_hybrid.nlargest(10, 'Rpn')[['Failure Mode', 'Rpn', 'Action Priority']]
    for idx, row in top_10.iterrows():
        print(f"{idx+1}. {row['Failure Mode'][:55]:<55} | RPN: {row['Rpn']:<4} | {row['Action Priority']}")
    
    # Export
    output_path = 'output/YOUR_HYBRID_FMEA.xlsx'
    generator.export_fmea(fmea_hybrid, output_path, format='excel')
    print(f"\n💾 Exported to: {output_path}")
    
    # Generate detailed summary
    summary = generate_summary_report(fmea_hybrid)
    
    # Save summary
    summary_path = 'output/YOUR_HYBRID_FMEA_SUMMARY.txt'
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"📄 Summary saved to: {summary_path}")
    
except Exception as e:
    print(f"\n❌ Error in hybrid analysis: {e}")

print("\n" + "=" * 70)
print("  ✨ PROCESSING COMPLETE!")
print("=" * 70)

print("\n📁 All outputs saved to 'output/' folder:")
print("   - YOUR_STRUCTURED_FMEA.xlsx")
print("   - YOUR_FORD_FMEA.xlsx")
print("   - YOUR_TOYOTA_FMEA.xlsx")
print("   - YOUR_HONDA_FMEA.xlsx")
print("   - YOUR_HYBRID_FMEA.xlsx")
print("   - YOUR_HYBRID_FMEA_SUMMARY.txt")

print("\n🚀 Next Steps:")
print("   1. Open output files in Excel to review results")
print("   2. Run dashboard for interactive analysis: streamlit run app.py")
print("   3. Process more brands by editing this script")

print("\n💡 Tips:")
print("   - Increase 'max_reviews_per_batch' for more comprehensive analysis")
print("   - Set config['model']['name'] to use LLM for better accuracy")
print("   - Customize risk scoring in config/config.yaml")

print("\n" + "=" * 70)
