from __future__ import annotations

from retrieval_research.config import get_settings


def _get() -> object:
    return get_settings()


GEMINI_MODEL = _get().gemini_model
MLX_MODEL_PATH = _get().mlx_model_path
OCR_MIN_DIM = _get().ocr_min_dim
OCR_MAX_DIM = _get().ocr_max_dim
