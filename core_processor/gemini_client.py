from __future__ import annotations

import os
from typing import Optional

from google import genai

_gemini_client: Optional[genai.Client] = None


def get_gemini_client() -> Optional[genai.Client]:
    global _gemini_client
    if _gemini_client is None:
        key = os.getenv("GEMINI_API_KEY")
        _gemini_client = genai.Client(api_key=key) if key else None
    return _gemini_client


def reset_gemini_client_for_tests() -> None:
    global _gemini_client
    _gemini_client = None
