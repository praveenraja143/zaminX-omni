"""
src/preprocessing.py
====================
Text preprocessing for Indian legal documents.
Handles multilingual court order text (English + Tamil + Hindi).
Used by the NLP summarizer and OCR pipeline.
"""

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Legal Text Cleaner
# ─────────────────────────────────────────────────────────────────────────────
class LegalTextPreprocessor:
    """
    Cleans and normalizes Indian court order text for NLP processing.

    Challenges:
    - Mix of English, Tamil, Hindi in same document
    - Inconsistent date formats (DD.MM.YYYY, DD-MM-YYYY, etc.)
    - Legal abbreviations (s/o, w/o, d/o, Vs., OS, CS, etc.)
    - OCR artifacts (extra spaces, misread characters)
    - Section references (Sec. 11, S. 6, Art. 300A)
    """

    # Legal abbreviations to expand for better NLP understanding
    LEGAL_ABBREV_MAP = {
        r"\bs/o\b": "son of",
        r"\bw/o\b": "wife of",
        r"\bd/o\b": "daughter of",
        r"\bVs\.\b": "versus",
        r"\bOS\b": "Original Suit",
        r"\bCS\b": "Civil Suit",
        r"\bRC\b": "Revenue Case",
        r"\bSA\b": "Second Appeal",
        r"\bCMA\b": "Civil Miscellaneous Appeal",
        r"\bHon\.\b": "Honourable",
        r"\bSr\.\b": "Senior",
        r"\bJr\.\b": "Junior",
        r"\bSmt\.\b": "Smt",
        r"\bThiru\b": "Thiru",    # Tamil honorific — keep as is
        r"\bPetitioner\b": "petitioner",
        r"\bRespondent\b": "respondent",
    }

    # Noise patterns to remove
    NOISE_PATTERNS = [
        r"\bPage\s+\d+\s+of\s+\d+\b",          # "Page 1 of 5"
        r"\bCIN:\s*[A-Z0-9]+\b",                # Court identification numbers
        r"={3,}",                                # separator lines
        r"-{3,}",                                # separator lines
        r"\s{3,}",                               # excessive whitespace
    ]

    def __init__(self):
        # Compile patterns once for efficiency
        self._abbrev_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.LEGAL_ABBREV_MAP.items()
        ]
        self._noise_patterns = [re.compile(p, re.IGNORECASE) for p in self.NOISE_PATTERNS]

    def clean(self, text: str, language: str = "en") -> str:
        """
        Full cleaning pipeline for court order text.

        Steps:
        1. Unicode normalization
        2. Remove noise patterns
        3. Expand abbreviations
        4. Normalize whitespace
        5. Fix common OCR errors
        """
        if not text or not text.strip():
            return ""

        # Step 1: Normalize unicode (handle Tamil/Hindi unicode variants)
        text = unicodedata.normalize("NFC", text)

        # Step 2: Remove noise
        for pattern in self._noise_patterns:
            text = pattern.sub(" ", text)

        # Step 3: Expand legal abbreviations (English only)
        if language == "en":
            for pattern, replacement in self._abbrev_patterns:
                text = pattern.sub(replacement, text)

        # Step 4: Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Step 5: Fix common OCR errors in Indian documents
        text = self._fix_ocr_errors(text)

        return text

    @staticmethod
    def _fix_ocr_errors(text: str) -> str:
        """Fix common OCR misreads in Indian legal documents."""
        # "O" misread as "0" in legal terms
        text = re.sub(r"\b0rder\b", "Order", text)
        text = re.sub(r"\b0wner\b", "Owner", text)
        # "l" misread as "1" in names
        text = re.sub(r"\b1and\b", "land", text)
        # Fix broken survey numbers like "12 3/4" → "123/4"
        text = re.sub(r"(\d+)\s+(\d+/\d+)", r"\1\2", text)
        return text

    def extract_key_entities(self, text: str) -> dict:
        """
        Extract key legal entities from court order text.

        Returns:
            {
                "survey_numbers": [...],
                "dates": [...],
                "parties": [...],
                "case_numbers": [...],
                "sections": [...],
            }
        """
        return {
            "survey_numbers": self._extract_survey_numbers(text),
            "dates": self._extract_dates(text),
            "case_numbers": self._extract_case_numbers(text),
            "sections": self._extract_legal_sections(text),
        }

    @staticmethod
    def _extract_survey_numbers(text: str) -> list:
        """Extract survey numbers from text. Indian formats: 123/4, S.No.123, Survey No.456"""
        patterns = [
            r"[Ss]urvey\s*[Nn]o\.?\s*(\d+(?:/\d+)?(?:[A-Z])?)",
            r"[Ss]\.?\s*[Nn]o\.?\s*(\d+(?:/\d+)?)",
            r"\b(\d{1,4}/\d{1,4}[A-Z]?)\b",    # standalone format like "45/2A"
        ]
        found = []
        for p in patterns:
            found.extend(re.findall(p, text))
        return list(set(found))

    @staticmethod
    def _extract_dates(text: str) -> list:
        """Extract dates in various Indian formats."""
        date_patterns = [
            r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b",
            r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
        ]
        dates = []
        for p in date_patterns:
            dates.extend(re.findall(p, text, re.IGNORECASE))
        return dates

    @staticmethod
    def _extract_case_numbers(text: str) -> list:
        """Extract case numbers like OS/123/2021, CS/45/2020."""
        pattern = r"\b([A-Z]{1,4}/\d+/\d{4})\b"
        return re.findall(pattern, text)

    @staticmethod
    def _extract_legal_sections(text: str) -> list:
        """Extract legal section references like 'Section 11', 'Article 300A'."""
        pattern = r"\b(?:Section|Sec\.|Art\.|Article)\s+(\d+[A-Z]?(?:\(\d+\))?)\b"
        return re.findall(pattern, text, re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Survey Number Normalizer
# ─────────────────────────────────────────────────────────────────────────────
def normalize_survey_number(survey_number: str) -> str:
    """
    Normalize survey number to canonical form.

    Examples:
        "123/4 A" → "123/4A"
        " 45/ 2 " → "45/2"
        "45" → "45"
    """
    if not survey_number:
        return ""
    # Remove extra spaces
    normalized = re.sub(r"\s+", "", survey_number.strip().upper())
    # Ensure consistent slash format
    normalized = re.sub(r"[\\|]", "/", normalized)
    return normalized


def normalize_village_name(village: str) -> str:
    """
    Normalize village name for consistent DB queries.

    Examples:
        "gobichettipalayam" → "Gobichettipalayam"
        "ERODE" → "Erode"
        "Salem  City" → "Salem City"
    """
    if not village:
        return ""
    # Collapse whitespace and title-case
    return " ".join(word.capitalize() for word in village.strip().split())


# ─────────────────────────────────────────────────────────────────────────────
# Image Preprocessor for OCR
# ─────────────────────────────────────────────────────────────────────────────
class ImagePreprocessor:
    """
    Preprocesses patta/chitta document images for Tesseract OCR.
    Handles poor quality photos taken on budget phones.
    """

    def __init__(self):
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
            self._available = True
        except ImportError:
            logger.warning("OpenCV not available. Image preprocessing disabled.")
            self._available = False

    def preprocess(self, image_path: str) -> Optional[str]:
        """
        Full preprocessing pipeline.
        Returns path to processed image ready for Tesseract.
        """
        if not self._available:
            return image_path

        cv2 = self.cv2
        np = self.np

        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                logger.error("Failed to load image: %s", image_path)
                return None

            # Step 1: Resize if too small (improves OCR accuracy)
            h, w = img.shape[:2]
            if max(h, w) < 1000:
                scale = 1000 / max(h, w)
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Step 2: Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Step 3: Denoise (important for photos with noise)
            denoised = cv2.fastNlMeansDenoising(gray, h=10)

            # Step 4: Adaptive thresholding (handles uneven lighting)
            thresh = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )

            # Step 5: Deskew (fix camera tilt)
            thresh = self._deskew(thresh)

            # Save processed image
            output_path = image_path.replace(".", "_processed.")
            cv2.imwrite(output_path, thresh)
            logger.info("Image preprocessed: %s → %s", image_path, output_path)
            return output_path

        except Exception as e:
            logger.error("Image preprocessing failed: %s", e)
            return image_path  # fallback to original

    def _deskew(self, image):
        """Correct skew angle in document images."""
        coords = self.np.column_stack(self.np.where(image > 0))
        angle = self.cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5:
            return image  # skip if nearly straight
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = self.cv2.getRotationMatrix2D(center, angle, 1.0)
        return self.cv2.warpAffine(image, M, (w, h), flags=self.cv2.INTER_CUBIC, borderMode=self.cv2.BORDER_REPLICATE)


# Module-level singleton
preprocessor = LegalTextPreprocessor()
image_preprocessor = ImagePreprocessor()
