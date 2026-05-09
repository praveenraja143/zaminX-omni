"""
ocr_engine.py — Tesseract OCR for scanned legal documents
Graceful: returns empty string if pytesseract is not installed.
"""
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    import io
    _HAS_OCR = True
except ImportError:
    _HAS_OCR = False
    logger.warning("pytesseract/Pillow not installed. OCR disabled.")


class OCREngine:
    def __init__(self):
        self.is_available = _HAS_OCR
        if _HAS_OCR:
            logger.info("OCR (Tesseract): READY")
        else:
            logger.info("OCR (Tesseract): DISABLED")

    def extract_text(self, image_bytes: bytes) -> str:
        if not _HAS_OCR:
            return ""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return pytesseract.image_to_string(image, lang='eng+tam')
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""


ocr_engine = OCREngine()
