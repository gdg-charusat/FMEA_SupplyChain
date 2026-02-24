"""
Quick Test - Verify system works with YOUR data
Fast test using rule-based extraction (no LLM needed)
"""

import sys
from pathlib import Path
import yaml
import pandas as pd

sys.path.append(str(Path(__file__).parent / 'src'))

print("\n" + "=" * 70)
print("  QUICK TEST - YOUR DATA")
print("=" * 70)

# Test 1: Check files
print("\nChecking your datasets...")

if Path('FMEA.csv').exists():
    # Read with error handling for malformed CSV
    df = pd.read_csv('FMEA.csv', encoding='utf-8', on_bad_lines='skip')
    print(f"[OK] FMEA.csv found: {len(df)} records")
else:
    print("[MISSING] FMEA.csv not found!")
    sys.exit(1)

review_files = list(Path('archive (3)').glob('*.csv'))
print(f"[OK] Car reviews found: {len(review_files)} brand files")

# Test 2: Quick processing test
print("\nTesting FMEA generation...")

try:
    from fmea_generator import FMEAGenerator
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Use rule-based for fast test
    config['model']['name'] = None
    config['text_processing']['max_reviews_per_batch'] = 10
    
    generator = FMEAGenerator(config)
    
    # Test structured data
    print("\n[1] Testing with FMEA.csv (structured)...")
    fmea_structured = generator.generate_from_structured('FMEA.csv')
    print(f"   [OK] Processed {len(fmea_structured)} failure modes")
    print(f"   [OK] Average RPN: {fmea_structured['Rpn'].mean():.1f}")
    
    # Test unstructured data (small sample)
    print("\n[2] Testing with car reviews (unstructured)...")
    test_file = 'archive (3)/Scraped_Car_Review_ford.csv'
    fmea_text = generator.generate_from_text(test_file, is_file=True)
    print(f"   [OK] Extracted {len(fmea_text)} failure modes from reviews")
    
    # Show sample output
    print("\nSample Results:")
    print(fmea_structured[['Component', 'Failure Mode', 'Rpn', 'Action Priority']].head(3).to_string())
    
    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED!")
    print("=" * 70)
    print("\nYour system is ready! Next steps:")
    print("   * Run full analysis: python process_my_data.py")
    print("   * Launch dashboard: streamlit run app.py")
    print("   * Run examples: python examples.py")
    print("")
    
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check if all dependencies installed: pip install -r requirements.txt")
    print("2. Verify NLTK data: python -c \"import nltk; nltk.download('punkt')\"")
    print("3. See SETUP.md for detailed instructions")
    sys.exit(1)
