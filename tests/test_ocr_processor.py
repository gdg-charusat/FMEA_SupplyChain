"""
Unit tests for OCRProcessor.
Run with: pytest tests/test_ocr_processor.py
"""

import io
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ocr_processor import OCRProcessor

fitz = pytest.importorskip("fitz")

try:
    import pytesseract
except ImportError:  # pragma: no cover - pytesseract is a required dependency
    pytesseract = None


def _tesseract_available() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _create_text_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def _create_image_only_pdf(path: Path, text: str) -> None:
    image = Image.new("RGB", (800, 300), color="white")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    draw.text((40, 40), text, fill="black", font=font)

    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    doc = fitz.open()
    page = doc.new_page(width=image.width, height=image.height)
    rect = fitz.Rect(0, 0, image.width, image.height)
    page.insert_image(rect, stream=image_bytes.getvalue())
    doc.save(str(path))
    doc.close()


@pytest.fixture
def processor() -> OCRProcessor:
    return OCRProcessor()


def test_extract_text_from_image_returns_text(processor: OCRProcessor) -> None:
    if not _tesseract_available():
        pytest.skip("Tesseract not available")

    image_path = Path(__file__).parent.parent / "test_images" / "failure_report_1.png"
    text = processor.extract_text_from_image(image_path)

    assert isinstance(text, str)
    assert len(text.strip()) > 10


def test_extract_text_from_image_accepts_bytes(processor: OCRProcessor) -> None:
    if not _tesseract_available():
        pytest.skip("Tesseract not available")

    image_path = Path(__file__).parent.parent / "test_images" / "failure_report_2.png"
    image_bytes = image_path.read_bytes()
    text = processor.extract_text_from_image(image_bytes)

    assert isinstance(text, str)
    assert len(text.strip()) > 10


def test_extract_text_from_pdf_direct_text(processor: OCRProcessor, tmp_path: Path) -> None:
    pdf_path = tmp_path / "direct_text.pdf"
    _create_text_pdf(pdf_path, "Direct PDF text extraction test")

    text = processor.extract_text_from_pdf(pdf_path)

    assert "direct pdf text extraction" in text.lower()


def test_extract_text_from_pdf_falls_back_to_ocr(processor: OCRProcessor, tmp_path: Path) -> None:
    if not _tesseract_available():
        pytest.skip("Tesseract not available")

    pdf_path = tmp_path / "scanned_text.pdf"
    _create_image_only_pdf(pdf_path, "Scanned OCR fallback test")

    text = processor.extract_text_from_pdf(pdf_path)

    assert len(text.strip()) > 10
