# =============================================================================
# vision/ocr.py
# Responsibility: Extract text from a single frame and return it as a string.
# Interface (FIXED — do not change signature):
#   read_text(frame: np.ndarray) -> str | None
# =============================================================================

import os
import sys
import tempfile
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    print("[ocr] WARNING: pytesseract not installed — Tesseract OCR disabled.")

try:
    from google import genai
    from google.genai import types as genai_types
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    print("[ocr] WARNING: google-genai not installed — Gemini fallback disabled.")

_GEMINI_PROMPT = (
    "Read all visible text in this image and return it as plain text only. "
    "No formatting, no markdown, no JSON. Just the raw text content as it "
    "appears. If the image is a menu, list each item on a new line. "
    "If no text is visible, return the single word: NONE"
)


def _preprocess(frame: np.ndarray) -> list:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray,
                               (config.OCR_BLUR_KERNEL, config.OCR_BLUR_KERNEL), 0)
    _, thresh = cv2.threshold(blurred, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_inv = cv2.bitwise_not(thresh)
    pad = config.OCR_PADDING
    variants = []
    for img in [thresh, thresh_inv]:
        padded = cv2.copyMakeBorder(img, pad, pad, pad, pad,
                                    cv2.BORDER_CONSTANT, value=255)
        variants.append(padded)
    return variants


def _run_tesseract(frame: np.ndarray):
    if not _TESSERACT_AVAILABLE:
        return None
    variants = _preprocess(frame)
    best = ""
    for img in variants:
        for cfg in config.OCR_TESSERACT_CONFIGS:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
                if len(text) > len(best):
                    best = text
            except Exception as e:
                print(f"[ocr] Tesseract error with config '{cfg}': {e}")
    return best if len(best) >= config.OCR_MIN_TEXT_LENGTH else None


def _run_gemini(frame: np.ndarray):
    if not _GEMINI_AVAILABLE:
        return None
    api_key = getattr(config, "GEMINI_API_KEY", "")
    if not api_key:
        print("[ocr] Gemini skipped — GEMINI_API_KEY not set in config.py")
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    try:
        cv2.imwrite(tmp.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        client = genai.Client(api_key=api_key)
        with open(tmp.name, "rb") as f:
            image_data = f.read()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                genai_types.Part.from_bytes(data=image_data,
                                            mime_type="image/jpeg"),
                _GEMINI_PROMPT
            ]
        )
        text = (getattr(response, "text", "") or "").strip()
        if not text or text.upper() == "NONE":
            return None
        return text
    except Exception as e:
        print(f"[ocr] Gemini error: {e}")
        return None
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


def read_text(frame: np.ndarray):
    """
    Extract text from a single BGR frame.
    Returns plain string or None.
    """
    text = _run_tesseract(frame)
    if text:
        print(f"[ocr] Tesseract: {repr(text[:80])}")
        return text

    print("[ocr] Tesseract found nothing — trying Gemini...")
    text = _run_gemini(frame)
    if text:
        print(f"[ocr] Gemini: {repr(text[:80])}")
        return text

    print("[ocr] No text detected.")
    return None