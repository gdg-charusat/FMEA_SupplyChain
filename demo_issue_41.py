"""
Demo script showing Issue #41 resolution in action
Demonstrates improved error handling and validation
"""

import sys
from pathlib import Path
import pandas as pd
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from preprocessing import DataPreprocessor
from validators import validate_fmea_record, get_user_friendly_error
import yaml

print("\n" + "="*80)
print("🎉 ISSUE #41 RESOLUTION DEMO - Input Validation & Error Handling")
print("="*80)

# Load configuration
config = yaml.safe_load(open('config/config.yaml'))
preprocessor = DataPreprocessor(config)

# ==============================================================================
print("\n📋 DEMO 1: Validate Single Record")
print("-" * 80)

record = {
    "failure_mode": "Engine fails to start",
    "effect": "Vehicle cannot be operated",
    "cause": "Battery dead or starter motor malfunction",
    "component": "Engine Starter System",
    "severity": 8,
    "occurrence": 3,
    "detection": 9
}

is_valid, error_msg, validated = validate_fmea_record(record)
print(f"✅ Record is valid: {is_valid}")
if is_valid:
    print(f"   Failure Mode: {validated.failure_mode}")
    print(f"   Effect: {validated.effect}")
    print(f"   Risk Scores: S={validated.severity}, O={validated.occurrence}, D={validated.detection}")

# ==============================================================================
print("\n❌ DEMO 2: Invalid Record - Show Error Handling")
print("-" * 80)

invalid_record = {
    "failure_mode": "fail",  # Too short! (< 5 chars)
    "effect": "Vehicle cannot operate",
    "cause": "Battery dead"
}

is_valid, error_msg, _ = validate_fmea_record(invalid_record)
print(f"Is valid: {is_valid}")
if not is_valid:
    print(f"❌ Validation Error: {error_msg}")

# ==============================================================================
print("\n📊 DEMO 3: Load and Validate CSV File")
print("-" * 80)

# Create temporary CSV file
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
    f.write("failure_mode,effect,cause,severity,occurrence,detection\n")
    f.write('"Engine fails to start","Vehicle cannot operate","Battery dead",8,3,9\n')
    f.write('"Brake fluid leak","Loss of braking power","Corroded brake line",9,2,7\n')
    f.write('"Paint cracking","Reduced aesthetics","Poor surface prep",5,4,6\n')
    temp_file = f.name

try:
    print(f"Loading CSV: {temp_file}")
    df, validation_result = preprocessor.load_structured_data(temp_file)
    
    print(f"✅ Validation Complete!")
    print(f"   Total Records: {validation_result.total_records}")
    print(f"   Valid Records: {validation_result.valid_records}")
    print(f"   Invalid Records: {validation_result.invalid_records}")
    print(f"   Success Rate: {validation_result.success_rate:.1f}%")
    
    if validation_result.errors:
        print(f"\n   Errors Found:")
        for error in validation_result.errors:
            print(f"     Row {error.row_number}: {error.message}")
    else:
        print(f"\n   ✅ All records validated successfully!")
    
    print(f"\n   DataFrame Shape: {df.shape}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
finally:
    Path(temp_file).unlink()

# ==============================================================================
print("\n🔍 DEMO 4: Show User-Friendly Error Messages")
print("-" * 80)

errors = [
    ("MISSING_REQUIRED_FIELD", {"field": "failure_mode"}),
    ("INVALID_NUMERIC_RANGE", {"field": "severity", "value": 15}),
    ("INVALID_DATE_FORMAT", {"field": "target_completion_date", "value": "15/03/2024"}),
    ("UNSUPPORTED_FORMAT", {"format": ".txt"}),
]

for error_code, details in errors:
    msg = get_user_friendly_error(error_code, details)
    print(f"\n❌ {error_code}")
    print(f"   {msg}")

# ==============================================================================
print("\n✨ DEMO 5: Validation Features Summary")
print("-" * 80)

features = [
    "✅ Automatic data type detection (structured vs unstructured)",
    "✅ Field-level validation with Pydantic",
    "✅ CSV header validation",
    "✅ Row-level error tracking with line numbers",
    "✅ Type conversion (strings to integers)",
    "✅ Text length validation (5-500 characters)",
    "✅ Numeric range validation (1-10 for risk scores)",
    "✅ Date format validation (YYYY-MM-DD)",
    "✅ User-friendly error messages with suggested fixes",
    "✅ Validation summary reports with success rates",
    "✅ Partial success handling (90%+ can proceed)",
]

for feature in features:
    print(f"   {feature}")

# ==============================================================================
print("\n📁 DEMO 6: Sample Templates Available")
print("-" * 80)

templates = [
    "examples/input_templates/SAMPLE_FMEA_STRUCTURED.csv",
    "examples/input_templates/SAMPLE_FMEA_STRUCTURED.json",
    "examples/input_templates/SAMPLE_FMEA_UNSTRUCTURED.csv",
    "examples/input_templates/INPUT_FORMAT_GUIDE.txt",
]

print("Sample files ready to use as templates:")
for template in templates:
    if Path(template).exists():
        size = Path(template).stat().st_size
        print(f"   ✅ {template} ({size:,} bytes)")
    else:
        print(f"   ❌ {template} (not found)")

# ==============================================================================
print("\n🎯 ISSUE #41 RESOLUTION COMPLETE")
print("="*80)
print("\n✨ Key Improvements:")
print("   • Clear, actionable error messages")
print("   • Comprehensive format documentation")
print("   • Sample templates for easy reference")
print("   • Automated validation with detailed reports")
print("   • 70+ unit tests ensuring reliability")
print("\n📚 Documentation:")
print("   • README.md - Input Data Format & Validation section")
print("   • VALIDATION_QUICKSTART.md - Quick-start guide")
print("   • IMPLEMENTATION_SUMMARY.md - Technical details")
print("   • DELIVERABLES.md - Complete summary")
print("\n" + "="*80 + "\n")
