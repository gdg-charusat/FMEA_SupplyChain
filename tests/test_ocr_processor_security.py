import pytest
from pathlib import Path
from src.ocr_processor import OCRProcessor

def test_ocr_processor_rejects_absolute_path():
    processor = OCRProcessor()
    with pytest.raises(ValueError, match="Absolute paths are not allowed"):
        processor.extract_text_from_image("/etc/passwd")

def test_ocr_processor_rejects_path_traversal():
    processor = OCRProcessor()
    with pytest.raises(ValueError, match="Path traversal.*not allowed"):
        processor.extract_text_from_image("../../../etc/passwd")
