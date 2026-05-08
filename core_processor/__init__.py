"""Document page OCR: GLM-OCR via MLX, optional Gemini refinement."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from core_processor.image_geometry import _crop_document, _resize_for_ocr
from core_processor.pipeline import process_page
from core_processor.settings import GEMINI_MODEL

__all__ = ["process_page", "GEMINI_MODEL", "_crop_document", "_resize_for_ocr"]
