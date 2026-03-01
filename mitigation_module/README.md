# LLM-Powered Automated FMEA Generator

<div align="center">

![FMEA Generator](https://img.shields.io/badge/FMEA-Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production-success)

**An intelligent system that automatically generates Failure Mode and Effects Analysis (FMEA) from both structured and unstructured data using Large Language Models**

</div>

---

## 📋 Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Architecture](#architecture)
* [Installation](#installation)
* [Quick Start](#quick-start)
* [Usage](#usage)
* [Configuration](#configuration)
* [Project Structure](#project-structure)
* [Examples](#examples)
* [API Reference](#api-reference)
* [FAQ](#-faq)
* [Contributing](#contributing)
* [License](#license)

---

## 🎯 Overview

Traditional FMEA is manual, time-consuming, and expert-dependent. This system revolutionizes the process by:

* **Automating extraction** of failure information from customer reviews, complaints, and reports
* **Processing structured data** from Excel/CSV files
* **Using LLMs** for intelligent semantic understanding
* **Computing risk scores** (Severity, Occurrence, Detection)
* **Generating actionable insights** with recommended actions

### Problem Statement

Organizations receive failure information in multiple formats:

* Unstructured: Customer reviews, complaint text, incident reports
* Structured: Excel spreadsheets, CSV files with failure data

This system provides a **unified, intelligent solution** to convert all these inputs into a standardized FMEA.

---

## ✨ Features

### Core Capabilities

* ✅ **Dual Input Support**: Process both structured and unstructured data
* 🤖 **LLM-Powered Extraction**: Uses Mistral/LLaMA/GPT models for intelligent entity extraction
* 📊 **Automated Risk Scoring**: Calculates S, O, D scores and RPN automatically
* 🎯 **Action Priority Classification**: Categorizes risks as Critical, High, Medium, Low
* 📈 **Visual Analytics**: Interactive dashboards with charts and risk matrices
* 💾 **Multiple Export Formats**: Excel, CSV, JSON
* 🔄 **Hybrid Processing**: Combine multiple data sources seamlessly
* 🚀 **Production-Ready**: Modular, extensible, well-documented code

### Technical Features

* **NLP Processing**: Sentiment analysis, keyword extraction, text cleaning
* **Rule-Based Fallback**: Works even without LLM for faster processing
* **Batch Processing**: Handle large datasets efficiently
* **Deduplication**: Intelligent removal of similar failure modes
* **Configurable**: YAML-based configuration for easy customization

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

* Python 3.9 or higher
* 8GB RAM minimum (16GB recommended for LLM)
* GPU (optional, for faster LLM inference)

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

```bash
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

### 🎯 Working with YOUR Data (FMEA.csv + Car Reviews)

**FASTEST WAY - Process your actual datasets:**

```bash
python process_my_data.py
```

This will automatically process:

* ✅ Your FMEA.csv (161 industrial failure modes)
* ✅ Car reviews from archive (3) folder (Ford, Toyota, Honda)
* ✅ Create hybrid analysis combining both
* ✅ Export all results to `output/` folder

📖 **See YOUR_DATA_GUIDE.md for detailed instructions on working with your datasets!**

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

## 📖 Usage

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
  name: "mistralai/Mistral-7B-Instruct-v0.2"
  max_length: 512
  temperature: 0.3
  device: "auto"
  quantization: true
```

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
  negative_threshold: 0.3
  max_reviews_per_batch: 100
  enable_sentiment_filter: true
```

---

## 📁 Project Structure

```
Symboisis/
├── src/
│   ├── preprocessing.py
│   ├── llm_extractor.py
│   ├── risk_scoring.py
│   ├── fmea_generator.py
│   └── utils.py
├── config/
│   └── config.yaml
├── output/
├── archive (3)/
├── app.py
├── cli.py
├── examples.py
├── requirements.txt
├── .env.example
└── README.md
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

| Failure Mode  | Effect            | Severity | Occurrence | Detection | RPN | Priority |
| ------------- | ----------------- | -------- | ---------- | --------- | --- | -------- |
| Brake failure | Unable to stop    | 10       | 7          | 8         | 560 | Critical |
| Engine seized | Vehicle breakdown | 9        | 6          | 7         | 378 | High     |

---

## 🔌 API Reference

(unchanged — keep existing content)

---

## ❓ FAQ

### 1. I get `ModuleNotFoundError: No module named 'nltk'` — what do I do?

This usually means dependencies or NLTK data were not installed correctly. Run `pip install -r requirements.txt` and then download the required datasets using:

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
```

These steps are also listed in SETUP.md.

---

### 2. The model takes forever to load / crashes with out-of-memory error

Large LLM models require significant RAM/GPU memory. You can run the system in faster rule-based mode using the `--no-model` flag in CLI. You can also enable quantization in `config/config.yaml` (`quantization: true`) to reduce memory usage.

---

### 3. I get `Error: .env file not found`

You need to create your environment file from the template. Copy `.env.example` to `.env` and edit it if needed:

```bash
copy .env.example .env
```

Most fields are optional unless you are using external APIs.

---

### 4. Streamlit opens but the dashboard is blank / shows no data

The dashboard does not display results until data is provided. Upload a CSV/Excel file or use the sample data option available in the interface, then click **Generate FMEA**.

---

### 5. Can I use this without a GPU?

Yes. The system works in CPU mode automatically if no GPU is available. Processing will be slower (see performance table in README), but rule-based mode can provide much faster results.

---

### 6. My CSV isn't being parsed correctly — wrong columns detected

Ensure your dataset uses the required column names such as `failure_mode`, `effect`, `cause`, and `component`. Refer to `YOUR_DATA_GUIDE.md` for the expected format and examples.

---

### 7. What is RPN and what do the scores mean?

RPN (Risk Priority Number) is calculated as **Severity × Occurrence × Detection**. Higher RPN values indicate higher risk and help prioritize which failures should be addressed first.

---

### 8. How do I contribute? Can I pick any issue?

Please read `CONTRIBUTING.md` before starting. Most projects follow a claim-before-start workflow, meaning you should comment on an issue to get it assigned before working on it.

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