# Input Validation Quick Start Guide

Get started with the new input validation and error handling features in the FMEA Generator.

---

## 📋 Quick Links

- **Format Guide:** See `examples/input_templates/INPUT_FORMAT_GUIDE.txt`
- **Sample Files:** Check `examples/input_templates/SAMPLE_*.csv` and `.json`
- **Full Documentation:** Read `README.md` section "Input Data Format & Validation"
- **Error Reference:** See README.md table for common validation errors

---

## ⚡ 5-Minute Setup

### Step 1: View Sample Files
```bash
# Open and copy a sample file as your template
cd examples/input_templates/
cat SAMPLE_FMEA_STRUCTURED.csv
# OR
cat SAMPLE_FMEA_STRUCTURED.json
```

### Step 2: Prepare Your Data
Format your data using the samples as reference:
- **Structured:** Use CSV or JSON with required fields
- **Unstructured:** Use CSV with `text` column containing reviews

### Step 3: Import into FMEA System
```bash
# Via Web Dashboard
streamlit run app.py
# Then upload your file in the dashboard

# OR Via CLI
python cli.py --structured your_data.csv --output result.xlsx
```

---

## ✅ Data Format Checklist

### For Structured Data (CSV/JSON):

- [ ] File has required columns: `failure_mode`, `effect`, `cause`
- [ ] Text fields are 5-500 characters each
- [ ] Risk scores (severity, occurrence, detection) are 1-10 integers
- [ ] Dates are in YYYY-MM-DD format
- [ ] No missing values in required fields

### For Unstructured Data (Reviews):

- [ ] Column named `text` or `review`
- [ ] Each text entry is at least 5 characters
- [ ] (Optional) `source` column with valid source type

---

## 🚀 Common Tasks

### Copy a Sample File
```bash
# Windows
copy examples\input_templates\SAMPLE_FMEA_STRUCTURED.csv my_data.csv

# Linux/Mac
cp examples/input_templates/SAMPLE_FMEA_STRUCTURED.csv my_data.csv
```

### Validate Your File Before Import
```python
import sys
sys.path.insert(0, 'src')

from preprocessing import DataPreprocessor
import yaml

config = yaml.safe_load(open('config/config.yaml'))
preprocessor = DataPreprocessor(config)

# Check your file
df, validation_result = preprocessor.load_structured_data('my_data.csv')

print(f"✅ Valid: {validation_result.valid_records}")
print(f"❌ Invalid: {validation_result.invalid_records}")
print(f"Success Rate: {validation_result.success_rate:.1f}%")

# See errors
for error in validation_result.errors:
    print(f"Row {error.row_number}: {error.message}")
```

### Run Tests
```bash
# Test validators
pytest tests/test_validators.py -v

# Test preprocessing
pytest tests/test_preprocessing_validation.py -v

# Run all tests
pytest tests/ -v
```

---

## ❌ Troubleshooting

### Error: "Missing required field: failure_mode"
**Solution:** Ensure your CSV/JSON has a `failure_mode` column/field with values

### Error: "Text is too short"
**Solution:** All text entries must be at least 5 characters long

### Error: "Invalid numeric range for severity: 15"
**Solution:** Risk scores must be between 1-10 (1=low, 10=critical)

### Error: "Invalid date format: 15/03/2024"
**Solution:** Use YYYY-MM-DD format (example: 2024-02-24)

### Error: "Unsupported file format: .txt"
**Solution:** Use CSV, Excel (.xlsx), or JSON format

---

## 📚 Complete Examples

### Example 1: Import CSV Structured Data

**File: my_failures.csv**
```csv
failure_mode,effect,cause,component,severity
"Engine fails to start","Cannot operate","Battery dead","Engine System",8
"Brake fluid leak","Safety risk","Corroded line","Brake System",9
```

**Command:**
```bash
python cli.py --structured my_failures.csv --output fmea.xlsx
```

### Example 2: Import JSON Structured Data

**File: my_failures.json**
```json
[
  {
    "failure_mode": "Engine fails to start",
    "effect": "Vehicle cannot operate",
    "cause": "Battery dead",
    "component": "Engine System",
    "severity": 8
  }
]
```

**Command:**
```bash
python cli.py --structured my_failures.json --output fmea.xlsx
```

### Example 3: Import Customer Reviews

**File: reviews.csv**
```csv
text,source
"Engine making loud noise and then failed","customer_review"
"Brake system failed suddenly in traffic","warranty_claim"
```

**Command:**
```bash
python cli.py --text reviews.csv --output fmea.xlsx
```

### Example 4: Python API Usage

```python
from preprocessing import DataPreprocessor
import yaml

config = yaml.safe_load(open('config/config.yaml'))
preprocessor = DataPreprocessor(config)

# Load with validation
df, result = preprocessor.batch_preprocess(
    'my_data.csv',
    return_validation_result=True
)

# Check validation
if result.is_valid:
    print(f"✅ All {result.valid_records} records are valid!")
else:
    print(f"⚠️ {result.invalid_records} records failed validation")
    for error in result.errors[:5]:  # Show first 5 errors
        print(f"  Row {error.row_number}: {error.message}")
        print(f"  Fix: {error.suggested_fix}")
```

---

## 🎯 Key Features

### Input Validation
- ✅ Automatic CSV/JSON parsing
- ✅ Field type validation
- ✅ Length checks (5-500 chars)
- ✅ Numeric range validation (1-10)
- ✅ Date format validation
- ✅ Enum validation for source types

### Error Handling
- ✅ User-friendly error messages
- ✅ Row-level error tracking
- ✅ Suggested fixes for each error
- ✅ Success rate reporting
- ✅ Partial success handling (90%+ can proceed)

### User Experience
- ✅ Sample templates provided
- ✅ Detailed formatting guide
- ✅ Clear error messages with emojis
- ✅ Validation reports with summaries

---

## 📞 Support

**Having issues?**

1. Check `examples/input_templates/INPUT_FORMAT_GUIDE.txt` for detailed rules
2. Review sample files to see correct formatting
3. Look at error message - it tells you exactly what to fix
4. Run validation test to check your data before importing

**Still stuck?**

- Review README.md "Input Data Format & Validation" section
- Check test files for usage examples
- See IMPLEMENTATION_SUMMARY.md for technical details

---

## ✨ Tips & Tricks

### Tip 1: Start with Sample Files
Copy a sample file and modify it - easiest way to get the format right

### Tip 2: Validate Before Importing
Use the validation API to check your file before uploading to the dashboard

### Tip 3: Use Partial Results
Even if 5 records fail, you can use the 95 valid ones - no need to fix everything

### Tip 4: Check the Guide
When confused about format, refer to `INPUT_FORMAT_GUIDE.txt` - has all the rules

### Tip 4: Review Sample Files
Sample files show real-world examples of properly formatted data

---

**Last Updated:** February 25, 2026
**Version:** 1.0
