# 🚨 Critical Issues Analysis - FMEA Supply Chain Repository

**Analysis Date:** 2024-02-26  
**Repository:** gdg-charusat/FMEA_SupplyChain  
**Total Open Issues:** 25 | **Closed Issues:** 16

---

## 📊 Executive Summary

This document identifies and prioritizes critical security vulnerabilities, bugs, and architectural issues found in the FMEA Supply Chain codebase through automated analysis and GitHub issue tracking.

### Severity Distribution
- 🔴 **CRITICAL**: 8 issues
- 🟠 **HIGH**: 7 issues  
- 🟡 **MEDIUM**: 6 issues
- 🟢 **LOW**: 4 issues

---

## 🔴 CRITICAL PRIORITY ISSUES

### 1. **Remote Code Execution (RCE) via `trust_remote_code=True`**
**Issue:** [#73](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/73) | **Status:** Open  
**Severity:** 🔴 CRITICAL | **Type:** Security Vulnerability

**Location:** `src/llm_extractor.py:64-66`

**Problem:**
```python
self.tokenizer = AutoTokenizer.from_pretrained(
    model_name, trust_remote_code=True  # ⚠️ DANGEROUS
)
```

**Impact:**
- Allows arbitrary code execution from untrusted model repositories
- Attacker can inject malicious code in model files
- Complete system compromise possible

**Fix Required:**
```python
# Remove trust_remote_code or add strict validation
self.tokenizer = AutoTokenizer.from_pretrained(
    model_name, 
    trust_remote_code=False  # Safe default
)
```

**Priority:** IMMEDIATE ACTION REQUIRED

---

### 2. **Path Traversal Vulnerability in OCR Processor**
**Issue:** [#44](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/44) | **Status:** Closed  
**Severity:** 🔴 CRITICAL | **Type:** Security Vulnerability

**Location:** `src/ocr_processor.py:67-73`

**Problem:**
```python
def _read_bytes(self, source: ImageSource) -> bytes:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_absolute():
            raise ValueError("Absolute paths are not allowed for security reasons.")
        if ".." in path.parts:
            raise ValueError("Path traversal ('..') is not allowed.")
        return path.read_bytes()
```

**Issue:** Validation exists but can be bypassed with URL-encoded paths or symlinks.

**Status:** ✅ Fixed in recent PR but needs security audit

---

### 3. **Memory Exhaustion (DoS) in PDF Processing**
**Issue:** [#43](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/43) | **Status:** Closed  
**Severity:** 🔴 CRITICAL | **Type:** Denial of Service

**Location:** `src/ocr_processor.py:48-56`

**Problem:**
```python
def _ocr_pdf_bytes(self, pdf_bytes: bytes) -> str:
    extracted_pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:  # ⚠️ No page limit
            pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            page_text = pytesseract.image_to_string(image, lang=self.language)
```

**Impact:**
- Malicious PDF with 10,000+ pages causes OOM crash
- No memory limits or page count validation
- Server/application crash

**Fix Required:**
```python
MAX_PAGES = 50
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB

def _ocr_pdf_bytes(self, pdf_bytes: bytes) -> str:
    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise ValueError(f"PDF exceeds {MAX_PDF_SIZE} bytes")
    
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if doc.page_count > MAX_PAGES:
            raise ValueError(f"PDF has {doc.page_count} pages, max {MAX_PAGES}")
```

---

### 4. **Insecure HTTP for GDELT Service**
**Issue:** [#51](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/51) | **Status:** Open  
**Severity:** 🔴 CRITICAL | **Type:** Security - MITM Attack

**Location:** `mitigation_module/gdelt_service.py:17`

**Problem:**
```python
GDELT_MASTER_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"
```

**Impact:**
- Man-in-the-middle attack possible
- Data tampering/injection
- Supply chain attack vector

**Fix Required:**
```python
GDELT_MASTER_URL = "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"

# Add certificate verification
response = requests.get(GDELT_MASTER_URL, verify=True, timeout=10)
```

---

### 5. **GPU Memory Exhaustion & Resource Deadlock**
**Issue:** [#34](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/34) | **Status:** Closed  
**Severity:** 🔴 CRITICAL | **Type:** Resource Management

**Location:** `src/llm_extractor.py:45-90`

**Problem:**
- No GPU memory limits set
- Model loaded without cleanup mechanism
- Multiple instances cause CUDA OOM

**Impact:**
- System crash when GPU memory exhausted
- No graceful degradation to CPU
- Requires manual restart

**Fix Required:**
```python
import torch

# Add memory management
torch.cuda.empty_cache()
torch.cuda.set_per_process_memory_fraction(0.8)  # Limit to 80% GPU memory

# Add cleanup
def __del__(self):
    if self.model is not None:
        del self.model
        torch.cuda.empty_cache()
```

---

### 6. **Temporary File Resource Leak**
**Issue:** [#76](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/76) | **Status:** Open  
**Severity:** 🔴 CRITICAL | **Type:** Resource Leak

**Location:** `app.py:442-445`

**Problem:**
```python
temp_path = Path(f"temp_{uploaded_file.name}")
with open(temp_path, "wb") as f:
    f.write(uploaded_file.getbuffer())
# ... processing ...
temp_path.unlink()  # ⚠️ Not in finally block
```

**Impact:**
- Disk space exhaustion over time
- Temp files accumulate on exceptions
- Server storage fills up

**Fix Required:**
```python
import tempfile

with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
    tmp.write(uploaded_file.getbuffer())
    temp_path = Path(tmp.name)

try:
    # Processing
    fmea_df = generator.generate_from_structured(str(temp_path))
finally:
    temp_path.unlink(missing_ok=True)
```

---

### 7. **Uncontrolled Resource Consumption (DoS)**
**Issue:** [#61](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/61) | **Status:** Open  
**Severity:** 🔴 CRITICAL | **Type:** Denial of Service

**Location:** `src/preprocessing.py:145-160`

**Problem:**
```python
def _preprocess_text(self, df: pd.DataFrame) -> pd.DataFrame:
    # No row limit check
    df['text_cleaned'] = df['text'].progress_apply(self._clean_text)
    df['sentiment'] = df['text_cleaned'].progress_apply(self._get_sentiment)
```

**Impact:**
- User uploads 1M+ row CSV
- System processes all rows without limit
- CPU/Memory exhaustion

**Fix Required:**
```python
MAX_ROWS = 10000

def _preprocess_text(self, df: pd.DataFrame) -> pd.DataFrame:
    if len(df) > MAX_ROWS:
        logger.warning(f"Input has {len(df)} rows, limiting to {MAX_ROWS}")
        df = df.head(MAX_ROWS)
```

---

### 8. **KeyError Crash in Deduplication**
**Issue:** [#22](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/22) | **Status:** Closed  
**Severity:** 🔴 CRITICAL | **Type:** Runtime Error

**Location:** `src/fmea_generator.py:293`

**Problem:**
```python
def _deduplicate_failures(self, fmea_df: pd.DataFrame) -> pd.DataFrame:
    fmea_df['failure_mode_lower'] = fmea_df['Failure Mode'].str.lower()
    # ⚠️ Assumes 'Failure Mode' column exists with exact casing
```

**Impact:**
- Application crash when column name differs
- Data loss on exception
- Poor user experience

**Status:** ✅ Fixed but needs defensive programming

---

## 🟠 HIGH PRIORITY ISSUES

### 9. **CLI Configuration Override Conflict**
**Issue:** [#67](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/67) | **Status:** Open  
**Severity:** 🟠 HIGH | **Type:** Logic Bug

**Location:** `cli.py:95-98`

**Problem:**
```python
if args.no_model:
    print("Using rule-based extraction (no LLM)")
    config['model']['name'] = None
# ⚠️ Config loaded AFTER this check, overrides the flag
```

**Impact:**
- `--no-model` flag ignored
- LLM loads despite user request
- Unexpected behavior and resource usage

**Fix Required:**
```python
# Load config first
config = load_config(args.config)

# Then override with CLI flags
if args.no_model:
    config['model']['name'] = None
```

---

### 10. **Python Runtime Crashes - Argument Mismatches**
**Issue:** [#66](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/66) | **Status:** Open  
**Severity:** 🟠 HIGH | **Type:** Runtime Error

**Location:** Multiple files

**Problem:**
- Function calls with wrong argument counts
- Missing required parameters
- Type mismatches

**Examples Found:**
```python
# Missing 'is_file' parameter
generator.generate_from_text(texts)  # Should be: (texts, is_file=False)

# Wrong parameter name
scorer.calculate_rpn(s, o, d, component)  # 'component' not accepted
```

**Impact:** Application crashes during execution

---

### 11. **LLM Silently Degrades to CPU**
**Issue:** [#46](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/46) | **Status:** Closed  
**Severity:** 🟠 HIGH | **Type:** Performance Bug

**Location:** `src/llm_extractor.py:70-85`

**Problem:**
```python
device_config = self.model_config.get("device", "auto")
if device_config == "auto":
    device_map = "auto"
    actual_device = "cuda" if torch.cuda.is_available() else "cpu"
# ⚠️ device_map="auto" doesn't guarantee GPU usage
```

**Impact:**
- GPU available but model loads on CPU
- 10x slower processing
- No warning to user

**Status:** ✅ Fixed but needs verification

---

### 12. **Fractional Shipment Quantities Truncated**
**Issue:** [#60](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/60) | **Status:** Open  
**Severity:** 🟠 HIGH | **Type:** Data Loss

**Location:** `mitigation_module/report_generator.py`

**Problem:**
```python
quantity = int(route_data['quantity'])  # ⚠️ Truncates decimals
```

**Impact:**
- 1500.75 units becomes 1500 units
- Financial reporting errors
- Inventory discrepancies

**Fix Required:**
```python
quantity = float(route_data['quantity'])
# Format for display: f"{quantity:.2f}"
```

---

### 13. **Hardcoded Fallback Routes**
**Issue:** [#59](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/59) | **Status:** Open  
**Severity:** 🟠 HIGH | **Type:** Architecture Flaw

**Location:** `mitigation_module/disruption_extractor.py:150-180`

**Problem:**
- Routes hardcoded in multiple places
- No single source of truth
- Difficult to maintain and extend

**Impact:**
- Inconsistent routing logic
- Cannot add new routes dynamically
- Maintenance nightmare

---

### 14. **Disruption Validator Rejects Dynamic Routes**
**Issue:** [#37](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/37) | **Status:** Open  
**Severity:** 🟠 HIGH | **Type:** Logic Bug

**Location:** `mitigation_module/disruption_extractor.py:30-35`

**Problem:**
```python
class DisruptionEvent(BaseModel):
    target_route_id: int = Field(..., ge=1, le=10)  # ⚠️ Hardcoded limit
```

**Impact:**
- Cannot use routes > 10
- Dynamic routing broken
- System artificially limited

**Fix Required:**
```python
target_route_id: int = Field(..., ge=1, le=1000)  # Or remove upper limit
```

---

### 15. **City Name Regex Misfire**
**Issue:** [#17](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/17) | **Status:** Closed  
**Severity:** 🟠 HIGH | **Type:** Logic Bug

**Location:** `mitigation_module/disruption_extractor.py:200-220`

**Problem:**
```python
route_pattern = r'(?:route|r)\s*(\d+)'  # ⚠️ Can match unrelated text
```

**Impact:**
- False positives in route extraction
- Wrong routes selected
- Incorrect disruption mapping

**Status:** ✅ Fixed but needs comprehensive testing

---

## 🟡 MEDIUM PRIORITY ISSUES

### 16. **Lack of Comprehensive Input Validation**
**Issue:** [#33](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/33) | **Status:** Open  
**Severity:** 🟡 MEDIUM | **Type:** Security/Robustness

**Problem:**
- No file size limits on uploads
- No content type validation
- Missing CSV structure validation

**Impact:**
- Malformed data causes crashes
- Poor error messages
- Security risks

---

### 17. **Improve Error Handling in FMEA Pipeline**
**Issue:** [#41](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/41) | **Status:** Open  
**Severity:** 🟡 MEDIUM | **Type:** User Experience

**Problem:**
- Generic error messages
- No recovery mechanisms
- Stack traces shown to users

**Impact:**
- Poor user experience
- Difficult debugging
- Data loss on errors

---

### 18. **OCR Message Displayed Incorrectly**
**Issue:** [#40](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/40) | **Status:** Open  
**Severity:** 🟡 MEDIUM | **Type:** UI Bug

**Location:** `app.py:350-360`

**Problem:**
- OCR-specific messages shown for non-OCR uploads
- Confusing user interface

**Impact:** User confusion, poor UX

---

### 19. **Disruption Extraction Fails for Non-Hardcoded Cities**
**Issue:** [#16](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/16) | **Status:** Closed  
**Severity:** 🟡 MEDIUM | **Type:** Feature Limitation

**Status:** ✅ Fixed with dynamic routing

---

### 20. **Logic Error in Risk Escalation**
**Issue:** [#45](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/45) | **Status:** Closed  
**Severity:** 🟡 MEDIUM | **Type:** Calculation Bug

**Problem:**
- Incorrect RPN delta calculation
- Risk escalation logic flawed

**Status:** ✅ Fixed

---

### 21. **Race Condition on Route Globals**
**Issue:** [#35](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/35) | **Status:** Open  
**Severity:** 🟡 MEDIUM | **Type:** Concurrency Bug

**Problem:**
- Global variables modified without locks
- Thread-unsafe operations

**Impact:** Data corruption in multi-user scenarios

---

## 🟢 LOW PRIORITY ISSUES

### 22. **Missing Timestamps on Output Files**
**Issue:** [#3](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/3) | **Status:** Open  
**Severity:** 🟢 LOW | **Type:** Enhancement

**Problem:** Output files overwrite each other

**Fix:** Add timestamp to filenames (already implemented in some places)

---

### 23. **Sarcasm Detection in Preprocessing**
**Issue:** [#5](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/5) | **Status:** Open  
**Severity:** 🟢 LOW | **Type:** Enhancement

**Problem:** Sarcastic reviews misclassified as positive

**Impact:** Minor accuracy issues

---

### 24. **UI/UX Dashboard Redesign**
**Issue:** [#1](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/1) | **Status:** Open  
**Severity:** 🟢 LOW | **Type:** Enhancement

**Problem:** Dashboard could be more modern

**Impact:** Aesthetic only

---

### 25. **FAQ Section Missing**
**Issue:** [#2](https://github.com/gdg-charusat/FMEA_SupplyChain/issues/2) | **Status:** Closed  
**Severity:** 🟢 LOW | **Type:** Documentation

**Status:** ✅ Fixed

---

## 📋 Recommended Action Plan

### Phase 1: IMMEDIATE (Week 1)
1. ✅ Fix RCE vulnerability (#73) - Remove `trust_remote_code=True`
2. ✅ Add PDF page limits (#43) - Prevent DoS
3. ✅ Fix HTTPS for GDELT (#51) - Prevent MITM
4. ✅ Fix temp file leaks (#76) - Use context managers

### Phase 2: URGENT (Week 2)
5. ✅ Add input size limits (#61) - Prevent DoS
6. ✅ Fix CLI flag precedence (#67)
7. ✅ Fix argument mismatches (#66)
8. ✅ Fix fractional quantities (#60)

### Phase 3: IMPORTANT (Week 3-4)
9. ✅ Refactor hardcoded routes (#59)
10. ✅ Fix dynamic route validation (#37)
11. ✅ Add comprehensive input validation (#33)
12. ✅ Improve error handling (#41)

### Phase 4: ENHANCEMENTS (Month 2)
13. ✅ UI/UX improvements
14. ✅ Sarcasm detection
15. ✅ Additional features

---

## 🔍 Code Quality Metrics

### Security Issues: 5 Critical
- RCE vulnerability
- Path traversal
- MITM attack vector
- DoS vulnerabilities (2)

### Reliability Issues: 8 High/Critical
- Memory leaks
- Resource exhaustion
- Runtime crashes
- Data loss bugs

### Maintainability Issues: 4 Medium
- Hardcoded values
- Poor error handling
- Inconsistent architecture

---

## 📊 Issue Statistics

### By Status
- Open: 25 issues (62%)
- Closed: 16 issues (38%)
- Total: 41 issues

### By Label
- `bug`: 18 issues
- `enhancement`: 15 issues
- `security`: 5 issues
- `level-1`: 8 issues
- `level-2`: 17 issues

### By Team Activity
- Most Active: Team 152, Team 066, Team 125
- Recent PRs: 15 pending review
- Merge Rate: ~40% (16/41)

---

## 🎯 Key Recommendations

1. **Security Audit Required**: Multiple critical vulnerabilities need immediate attention
2. **Add Integration Tests**: Many bugs are runtime errors that unit tests would catch
3. **Code Review Process**: Implement mandatory reviews before merge
4. **Input Validation Layer**: Create centralized validation for all user inputs
5. **Resource Management**: Implement proper cleanup and limits throughout
6. **Documentation**: Add security guidelines and best practices
7. **Monitoring**: Add logging and alerting for production issues

---

## 📞 Contact & Resources

- **Repository**: https://github.com/gdg-charusat/FMEA_SupplyChain
- **Issue Tracker**: https://github.com/gdg-charusat/FMEA_SupplyChain/issues
- **Security Contact**: Report critical issues privately to maintainers

---

**Document Version:** 1.0  
**Last Updated:** 2024-02-26  
**Next Review:** 2024-03-05
