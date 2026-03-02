# LLM-Powered Automated FMEA Generator

<div align="center">

![FMEA Generator](https://img.shields.io/badge/FMEA-Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production-success)
![Security](https://img.shields.io/badge/Security-Hardened-brightgreen)

**An intelligent system that automatically generates Failure Mode and Effects Analysis (FMEA) from both structured and unstructured data using Large Language Models**

</div>

---

## 🔒 Security Notice

**Critical Security Fix Applied**: This system has been hardened against supply chain attacks. The LLM loader now:
- ✅ Blocks arbitrary code execution from untrusted model repositories
- ✅ Validates models against a trusted whitelist
- ✅ Uses `trust_remote_code=False` for all model loading

📖 **See [SECURITY_FIX.md](SECURITY_FIX.md) for complete details** | [Quick Reference](SECURITY_QUICKREF.md)

---

## 📋 Table of Contents

- [Security Notice](#-security-notice)
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Traditional FMEA is manual, time-consuming, and expert-dependent. This system revolutionizes the process by:

- **Automating extraction** of failure information from customer reviews, complaints, and reports
- **Processing structured data** from Excel/CSV files
- **Using LLMs** for intelligent semantic understanding
- **Computing risk scores** (Severity, Occurrence, Detection)
- **Generating actionable insights** with recommended actions

### Problem Statement

Organizations receive failure information in multiple formats:
- Unstructured: Customer reviews, complaint text, incident reports
- Structured: Excel spreadsheets, CSV files with failure data

This system provides a **unified, intelligent solution** to convert all these inputs into a standardized FMEA.

---

## ✨ Features

### Core Capabilities

- ✅ **Dual Input Support**: Process both structured and unstructured data
- 🤖 **LLM-Powered Extraction**: Uses Mistral/LLaMA/GPT models for intelligent entity extraction
- 📊 **Automated Risk Scoring**: Calculates S, O, D scores and RPN automatically
- 🎯 **Action Priority Classification**: Categorizes risks as Critical, High, Medium, Low
- 📈 **Visual Analytics**: Interactive dashboards with charts and risk matrices
- 💾 **Multiple Export Formats**: Excel, CSV, JSON
- 🔄 **Hybrid Processing**: Combine multiple data sources seamlessly
- 🚀 **Production-Ready**: Modular, extensible, well-documented code

### Technical Features

- **NLP Processing**: Sentiment analysis, keyword extraction, text cleaning
- **Rule-Based Fallback**: Works even without LLM for faster processing
- **Batch Processing**: Handle large datasets efficiently
- **Deduplication**: Intelligent removal of similar failure modes
- **Configurable**: YAML-based configuration for easy customization
- **Security Hardened**: Protected against supply chain attacks with model whitelist

---

## 🏗️ Architecture

```
User Input (Text/CSV/Excel)
         ↓
┌────────────────────┐
│  Data Preprocessing │ ← Text cleaning, validation, sentiment analysis
└────────────────────┘
         ↓
┌────────────────────┐
│  LLM Extraction     │ ← Extract: Failure Mode, Effect, Cause, Component
└────────────────────┘
         ↓
┌────────────────────┐
│  Risk Scoring       │ ← Calculate: Severity, Occurrence, Detection
└────────────────────┘
         ↓
┌────────────────────┐
│  FMEA Generator     │ ← Compute RPN, prioritize, recommend actions
└────────────────────┘
         ↓
┌────────────────────┐
│  Output & Export    │ ← Dashboard, Excel, CSV, JSON
└────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- 8GB RAM minimum (16GB recommended for LLM)
- GPU (optional, for faster LLM inference)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd Symboisis
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Download NLTK Data

```python
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
```

### Step 5: (Optional) Install spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### Step 6: Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your settings (optional)
```

---

## ⚡ Quick Start

### 🎯 **Working with YOUR Data (FMEA.csv + Car Reviews)**

**FASTEST WAY - Process your actual datasets:**
```bash
python process_my_data.py
```

This will automatically process:
- ✅ Your FMEA.csv (161 industrial failure modes)
- ✅ Car reviews from archive (3) folder (Ford, Toyota, Honda)
- ✅ Create hybrid analysis combining both
- ✅ Export all results to `output/` folder

📖 **See [YOUR_DATA_GUIDE.md](YOUR_DATA_GUIDE.md) for detailed instructions on working with your datasets!**

---

### Option 1: Web Dashboard (Recommended)

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501` in your browser.

### Option 2: Command Line

```bash
# From unstructured text
python cli.py --text reviews.csv --output fmea_output.xlsx

# From structured data
python cli.py --structured failures.csv --output fmea_output.xlsx

# Hybrid mode
python cli.py --text reviews.csv --structured failures.csv --output fmea_output.xlsx
```

### Option 3: Run Examples

```bash
python examples.py
```

This will run 3 demonstration examples and generate sample FMEAs.

---

## 📋 Input Data Format & Validation

### Data Format Requirements

To ensure successful FMEA generation, your input data must follow specific formats:

#### **Structured Data (CSV/JSON)**

**Required Fields:**
- `failure_mode` - Description of how/why the component could fail (5-500 chars)
- `effect` - Consequence or impact of the failure (5-500 chars)
- `cause` - Root cause(s) of the failure (5-500 chars)

**Optional Fields:**
- `component` - Component/subsystem affected
- `process` - Process where failure occurs
- `severity` - Score 1-10 (1=low, 10=critical)
- `occurrence` - Score 1-10 (1=rare, 10=very likely)
- `detection` - Score 1-10 (1=easy to detect, 10=impossible)
- `existing_controls` - Current preventive/detective controls
- `recommended_action` - Suggested action to eliminate/reduce risk
- `responsibility` - Person/department responsible for action
- `target_completion_date` - Deadline (YYYY-MM-DD format)

**CSV Example:**
```csv
failure_mode,effect,cause,component,severity,occurrence,detection
"Engine fails to start","Vehicle cannot operate","Battery dead","Engine System",8,3,9
"Brake fluid leak","Loss of braking power","Corroded line","Brake System",9,2,7
```

**JSON Example:**
```json
[
  {
    "failure_mode": "Engine fails to start",
    "effect": "Vehicle cannot operate",
    "cause": "Battery dead or starter malfunction",
    "component": "Engine Starter System",
    "severity": 8,
    "occurrence": 3,
    "detection": 9
  }
]
```

#### **Unstructured Data (Customer Reviews/Text)**

**Required Field:**
- `text` OR `review` - Raw text content (minimum 5 characters)

**Optional Field:**
- `source` - Type of source: `review`, `complaint`, `incident_report`, `customer_feedback`, `qa_report`, `warranty_claim`, `field_report`, `test_report`, or `other`

**CSV Example:**
```csv
text,source
"Engine started making loud noises and eventually failed","customer_review"
"Brake system malfunction caused dangerous situation on highway","warranty_claim"
```

### ✅ Validation & Error Handling

The system now includes **comprehensive input validation** using Pydantic schemas:

✨ **Features:**
- ✔️ Automatic detection of structured vs unstructured data
- ✔️ Field-level validation with type checking
- ✔️ User-friendly error messages with suggested fixes
- ✔️ Column header validation
- ✔️ Numeric range validation (1-10 for risk scores)
- ✔️ Date format validation (YYYY-MM-DD)
- ✔️ Detailed validation reports with success rates

📚 **Sample Templates:**

See `examples/input_templates/` for complete templates:
- `SAMPLE_FMEA_STRUCTURED.csv` - CSV format example
- `SAMPLE_FMEA_STRUCTURED.json` - JSON format example
- `SAMPLE_FMEA_UNSTRUCTURED.csv` - Unstructured text example
- `INPUT_FORMAT_GUIDE.txt` - Detailed formatting guide

### Common Validation Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required field: failure_mode` | Column not present in file | Ensure CSV/JSON has the required column |
| `Text is too short` | Text < 5 characters | Provide text with at least 5 characters |
| `Invalid numeric range for severity: 15` | Score outside 1-10 | Use values between 1 and 10 only |
| `Invalid date format: 15/03/2024` | Wrong date format | Use YYYY-MM-DD format (e.g., 2024-03-15) |
| `Unsupported file format: .txt` | File type not supported | Use CSV, Excel (.xlsx), or JSON format |
| `File is empty` | No data in file | Ensure file has at least 1 data record |

---

##  Usage

### 1. Using the Web Dashboard

1. **Start the dashboard**: `streamlit run app.py`
2. **Select input type**: Unstructured, Structured, or Hybrid
3. **Upload files** or paste text
4. **Click "Generate FMEA"**
5. **View results**: Metrics, tables, charts
6. **Export**: Download as Excel or CSV

### 2. Using Python API

```python
from fmea_generator import FMEAGenerator
import yaml

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize generator
generator = FMEAGenerator(config)

# Generate from text
reviews = ["Brake failure on highway...", "Engine overheated..."]
fmea_df = generator.generate_from_text(reviews, is_file=False)

# Generate from structured file
fmea_df = generator.generate_from_structured('data.csv')

# Export
generator.export_fmea(fmea_df, 'output/fmea.xlsx', format='excel')
```

### 3. Using CLI

```bash
# Basic usage
python cli.py --text input.csv --output result.xlsx

# With summary report
python cli.py --text input.csv --output result.xlsx --summary

# Faster rule-based mode (no LLM)
python cli.py --text input.csv --output result.xlsx --no-model

# Custom configuration
python cli.py --text input.csv --config custom_config.yaml --output result.xlsx
```

---

## ⚙️ Configuration

Edit `config/config.yaml` to customize:

### Model Settings

```yaml
model:
  name: "mistralai/Mistral-7B-Instruct-v0.2"  # LLM model (must be in trusted whitelist)
  max_length: 512
  temperature: 0.3
  device: "auto"  # auto, cuda, cpu
  quantization: true  # Use 4-bit quantization
```

**Security Note**: Only whitelisted models are allowed. See [SECURITY_FIX.md](SECURITY_FIX.md) for the list of trusted models.

### Risk Scoring Parameters

```yaml
risk_scoring:
  severity:
    high_keywords: ["critical", "catastrophic", "severe"]
    medium_keywords: ["moderate", "significant"]
    low_keywords: ["minor", "slight"]
    default: 5
```

### Text Processing

```yaml
text_processing:
  min_review_length: 10
  negative_threshold: 0.3  # Sentiment threshold
  max_reviews_per_batch: 100
  enable_sentiment_filter: true
```

---

## 📁 Project Structure

```
FMEA_SupplyChain/
├── src/
│   ├── preprocessing.py           # Data preprocessing with validation
│   ├── validators.py              # Input validation schemas (Pydantic)
│   ├── llm_extractor.py           # LLM-based extraction
│   ├── risk_scoring.py            # Risk scoring engine
│   ├── fmea_generator.py          # Main FMEA generator
│   ├── ocr_processor.py           # OCR for images/PDFs
│   └── utils.py                   # Utility functions
├── config/
│   └── config.yaml                # Configuration file
├── examples/
│   └── input_templates/           # 📋 Sample data templates
│       ├── SAMPLE_FMEA_STRUCTURED.csv
│       ├── SAMPLE_FMEA_STRUCTURED.json
│       ├── SAMPLE_FMEA_UNSTRUCTURED.csv
│       └── INPUT_FORMAT_GUIDE.txt
├── tests/
│   ├── test_validators.py         # ✅ Unit tests for validation
│   ├── test_preprocessing_validation.py  # ✅ Integration tests
│   └── test_*.py                  # Other tests
├── output/                        # Generated FMEA outputs
├── archive/                       # Sample data
├── app.py                         # Streamlit dashboard
├── cli.py                         # Command-line interface
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 📊 Examples

### Example 1: Customer Reviews

```python
reviews = [
    "Brake failure during heavy rain, very dangerous!",
    "Engine overheated and seized, no warning lights."
]

fmea_df = generator.generate_from_text(reviews, is_file=False)
```

**Output:**

| Failure Mode | Effect | Severity | Occurrence | Detection | RPN | Priority |
|-------------|--------|----------|------------|-----------|-----|----------|
| Brake failure | Unable to stop | 10 | 7 | 8 | 560 | Critical |
| Engine seized | Vehicle breakdown | 9 | 6 | 7 | 378 | High |

### Example 2: Structured Data

**Input CSV:**
```csv
failure_mode,effect,cause,component
Brake system failure,Cannot stop vehicle,Worn brake pads,Brake System
Engine overheating,Engine damage,Coolant leak,Cooling System
```

```python
fmea_df = generator.generate_from_structured('failures.csv')
```

### Example 3: Real Car Reviews

```python
# Process actual car review data
fmea_df = generator.generate_from_text('archive (3)/Scraped_Car_Review_ford.csv', is_file=True)

# Generate summary
from utils import generate_summary_report
print(generate_summary_report(fmea_df))
```

---

## 🔌 API Reference

### FMEAGenerator

Main class for FMEA generation.

#### Methods

**`generate_from_text(text_input, is_file=False)`**
- Generate FMEA from unstructured text
- Args: `text_input` (str or list), `is_file` (bool)
- Returns: DataFrame

**`generate_from_structured(file_path)`**
- Generate FMEA from structured CSV/Excel
- Args: `file_path` (str)
- Returns: DataFrame

**`generate_hybrid(structured_file, text_input)`**
- Generate FMEA from both sources
- Args: `structured_file` (str), `text_input` (str or list)
- Returns: DataFrame

**`export_fmea(fmea_df, output_path, format='excel')`**
- Export FMEA to file
- Args: `fmea_df` (DataFrame), `output_path` (str), `format` (str)

### DataPreprocessor

Handles data cleaning and preprocessing.

### LLMExtractor

Extracts failure information using LLMs.

### RiskScoringEngine

Calculates risk scores and RPN.

---

## 🧪 Testing

Run the examples to test the system:

```bash
python examples.py
```

This will:
1. Generate FMEA from sample reviews
2. Process structured data
3. Analyze real car reviews (if available)

---

## 🎯 Use Cases

### Manufacturing
- Analyze equipment failure reports
- Process quality control data
- Generate preventive maintenance schedules

### Automotive
- Process customer complaints
- Analyze warranty claims
- Identify safety issues

### Healthcare
- Analyze adverse event reports
- Process medical device failures
- Improve patient safety

### Software
- Analyze bug reports
- Process incident tickets
- Identify system vulnerabilities

---

## 🔬 Research Applications

This system is suitable for:
- Academic research papers
- Case studies
- Benchmarking studies
- Tool comparisons
- Industry reports

**Key Advantages:**
- Reproducible results
- Configurable parameters
- Comprehensive logging
- Export capabilities

---

## 🛠️ Troubleshooting

### Issue: Model loading fails

```bash
# Check if model is in trusted whitelist (see SECURITY_FIX.md)
# Or use rule-based mode instead
python cli.py --text input.csv --output result.xlsx --no-model
```

### Issue: "Model not in trusted whitelist" error

- **Cause**: Attempting to load an untrusted model
- **Solution**: Use a model from the trusted whitelist (see [SECURITY_FIX.md](SECURITY_FIX.md))
- **Alternative**: Use rule-based mode with `--no-model` flag

### Issue: Out of memory

- Enable quantization in config.yaml
- Use smaller batch sizes
- Use rule-based mode

### Issue: Slow processing

- Use GPU if available
- Enable quantization
- Reduce batch size
- Use rule-based mode for faster results

---

## 📈 Performance

### Processing Speed

| Mode | Speed | Accuracy |
|------|-------|----------|
| LLM (GPU) | ~2 reviews/sec | High |
| LLM (CPU) | ~0.3 reviews/sec | High |
| Rule-based | ~50 reviews/sec | Medium |

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB |
| GPU | None | 8GB VRAM |
| Disk | 2GB | 10GB |

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Authors

Developed as a production-grade academic and industry project for automated FMEA generation.

---

## 🙏 Acknowledgments

- HuggingFace for transformer models
- Streamlit for dashboard framework
- Open-source community

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the documentation
- Run examples for guidance

---

## 🚀 Future Enhancements

- [ ] Fine-tuned domain-specific models
- [ ] Fuzzy FMEA support
- [ ] Real-time monitoring
- [ ] Multi-language support
- [ ] Integration with PLM systems
- [ ] Advanced analytics
- [ ] Mobile app

---

<div align="center">

**⚠️ LLM-Powered FMEA Generator**

*Transforming failure analysis with AI*

</div>
