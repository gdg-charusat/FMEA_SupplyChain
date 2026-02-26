"""
OCR processing helpers for images and PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from PIL import Image
import pytesseract
import fitz


ImageSource = Union[bytes, bytearray, BytesIO, Path, str]


@dataclass
class OCRProcessor:
    """Extracts text from images and PDFs using Tesseract."""

    language: str = "eng"
    tesseract_cmd: Optional[str] = None

    def __post_init__(self) -> None:
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def extract_text_from_image(self, image_source: ImageSource) -> str:
        """Extract text from an image using OCR."""
        image_bytes = self._read_bytes(image_source)
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=self.language)
        return text.strip()

    def extract_text_from_pdf(self, pdf_source: ImageSource) -> str:
        """Extract text from PDF, falling back to OCR for scanned PDFs."""
        pdf_bytes = self._read_bytes(pdf_source)
        direct_text = self._extract_pdf_text(pdf_bytes)
        if direct_text.strip():
            return direct_text.strip()

        return self._ocr_pdf_bytes(pdf_bytes).strip()

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pages_text = [page.get_text("text") for page in doc]
        return "\n".join(pages_text)

    def _ocr_pdf_bytes(self, pdf_bytes: bytes) -> str:
        extracted_pages = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                page_text = pytesseract.image_to_string(image, lang=self.language)
                if page_text.strip():
                    extracted_pages.append(page_text.strip())
        return "\n".join(extracted_pages)

    def _read_bytes(self, source: ImageSource) -> bytes:
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.is_absolute():
                raise ValueError("Absolute paths are not allowed for security reasons.")
            if ".." in path.parts:
                raise ValueError("Path traversal ('..') is not allowed.")
            return path.read_bytes()
        if hasattr(source, "read"):
            data = source.read()
            if isinstance(data, str):
                return data.encode("utf-8")
            return bytes(data)
        raise TypeError("Unsupported source type for OCR")
