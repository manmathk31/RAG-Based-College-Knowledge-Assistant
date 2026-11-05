"""Tesseract OCR wrapper for selective optical character recognition."""

import logging
import shutil
from typing import Optional
from PIL import Image
import pytesseract
from pytesseract.pytesseract import TesseractNotFoundError as PyTesseractNotFoundError

from app.core.config import Settings, get_settings
from app.core.exceptions import OCRError, TesseractNotFoundError

logger = logging.getLogger(__name__)


class TesseractOCRExtractor:
    """Encapsulates Tesseract OCR image text extraction with availability checks and error handling."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._tesseract_cmd = self._settings.TESSERACT_CMD
        pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

    def is_available(self) -> bool:
        """Check whether the Tesseract executable is present on the system."""
        # 1. Check if directly in PATH or absolute executable
        if shutil.which(self._tesseract_cmd):
            return True
        # 2. Check via pytesseract get_tesseract_version
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text_from_image(self, image: Image.Image, page_number: int = 1) -> str:
        """Extract text from a PIL Image using Tesseract OCR.

        Args:
            image: PIL Image instance (e.g., rasterized PDF page).
            page_number: 1-indexed page number for contextual logging.

        Returns:
            Extracted text string.

        Raises:
            TesseractNotFoundError: If Tesseract executable is not installed or not in PATH.
            OCRError: If Tesseract execution fails.
        """
        if not self.is_available():
            raise TesseractNotFoundError(
                f"Tesseract OCR executable was not found at '{self._tesseract_cmd}'. "
                "Ensure Tesseract is installed (e.g., UB-Mannheim on Windows or `sudo apt install tesseract-ocr` on Linux) "
                "and accessible via PATH, or set OCR_ENABLED=false."
            )

        try:
            logger.info("Performing OCR on page %d (image size: %dx%d)...", page_number, image.width, image.height)
            text: str = pytesseract.image_to_string(image)
            clean_text = text.strip()
            logger.debug("OCR extracted %d characters from page %d.", len(clean_text), page_number)
            return clean_text
        except PyTesseractNotFoundError as exc:
            raise TesseractNotFoundError(f"Tesseract binary not found during OCR on page {page_number}: {exc}") from exc
        except Exception as exc:
            logger.error("Tesseract OCR execution failed on page %d: %s", page_number, exc)
            raise OCRError(f"OCR execution failed on page {page_number}: {exc}") from exc

