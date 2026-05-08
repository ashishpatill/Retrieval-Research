from __future__ import annotations

import logging
import os
from typing import Optional

from google import genai
from google.genai import errors as genai_errors

from retrieval_research.log import get_logger

_logger = get_logger("core_processor.gemini")
_gemini_client: Optional[genai.Client] = None


def get_gemini_client() -> Optional[genai.Client]:
    global _gemini_client
    if _gemini_client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            _logger.warning("GEMINI_API_KEY not set — cloud OCR refinement unavailable")
            return None
        try:
            _gemini_client = genai.Client(api_key=key)
        except Exception as exc:
            _logger.error("Failed to create Gemini client: %s", exc)
            return None
    return _gemini_client


def reset_gemini_client_for_tests() -> None:
    global _gemini_client
    _gemini_client = None


def safe_generate_content(model_name: str, contents: list, retries: int = 2) -> Optional[str]:
    client = get_gemini_client()
    if not client:
        return None
    for attempt in range(1 + retries):
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            return response.text
        except genai_errors.APIError as exc:
            _logger.error("Gemini API error (attempt %d/%d): %s", attempt, 1 + retries, exc)
            if attempt >= retries:
                return None
        except Exception as exc:
            _logger.error("Gemini unexpected error (attempt %d/%d): %s", attempt, 1 + retries, exc)
            if attempt >= retries:
                return None
    return None
