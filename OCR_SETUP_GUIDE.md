# OCR Setup Guide

This project uses Tesseract OCR through the `pytesseract` Python package. Tesseract is an OS-level dependency and must be installed separately.

## Windows

Option A: Installer (recommended)
1. Download the latest installer from the official Windows build:
   - https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer.
3. Add the Tesseract install directory to your PATH (for example, `C:\Program Files\Tesseract-OCR`).

Option B: Winget
```
winget install --id UB-Mannheim.TesseractOCR
```

Option C: Chocolatey
```
choco install tesseract
```

## macOS

Using Homebrew:
```
brew install tesseract
```

## Linux

Ubuntu / Debian:
```
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

Fedora:
```
sudo dnf install -y tesseract
```

CentOS / RHEL:
```
sudo yum install -y tesseract
```

## Verify Installation

After installing, verify the binary is available:
```
tesseract --version
```

If `pytesseract` cannot find the binary, set the path in code:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

## Python Dependencies

These packages are already listed in `requirements.txt`:
- pytesseract
- Pillow
- PyMuPDF

Install them with:
```
pip install -r requirements.txt
```
