from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppSettings:
    # ── Storage ──────────────────────────────────────────────────────────
    data_root: str

    # ── API keys ─────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── OCR / Ingestion ──────────────────────────────────────────────────
    gemini_model: str = "gemini-3.1-pro-preview"
    mlx_model_path: str = "mlx-community/GLM-OCR-6bit"
    ocr_min_dim: int = 1200
    ocr_max_dim: int = 2400
    default_ocr_mode: str = "Hybrid"
    default_dpi: int = 150

    # ── Chunking ─────────────────────────────────────────────────────────
    default_chunk_max_words: int = 220
    default_chunk_overlap_words: int = 40

    # ── BM25 ─────────────────────────────────────────────────────────────
    default_bm25_k1: float = 1.5
    default_bm25_b: float = 0.75

    # ── Dense ────────────────────────────────────────────────────────────
    default_dense_dimensions: int = 384

    # ── Late interaction ─────────────────────────────────────────────────
    default_late_dimensions: int = 128
    default_late_max_doc_tokens: int = 256

    # ── Visual ───────────────────────────────────────────────────────────
    default_visual_dimensions: int = 384
    default_visual_backend: str = "baseline"
    default_visual_compression: str = "none"

    # ── ColPali ──────────────────────────────────────────────────────────
    default_colpali_model: str = "vidore/colpali-v1.2"
    default_device: str = "auto"

    # ── Retrieval ────────────────────────────────────────────────────────
    default_top_k: int = 5
    default_retrieval_mode: str = "planner"
    default_planner_merge_strategy: str = "score_max"
    default_planner_rerank: bool = True
    default_route_vote_bonus: float = 0.08
    default_rerank_overlap_weight: float = 0.10


def _env_str(key: str, default: str) -> str:
    return (os.environ.get(key) or default).strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is not None:
        try:
            return int(raw.strip())
        except (ValueError, TypeError):
            pass
    return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is not None:
        try:
            return float(raw.strip())
        except (ValueError, TypeError):
            pass
    return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return default


@lru_cache
def get_settings() -> AppSettings:
    load_dotenv()
    return AppSettings(
        # Storage
        data_root=_env_str("RR_DATA_ROOT", "data"),
        # API keys
        gemini_api_key=_env_str("GEMINI_API_KEY", ""),
        # OCR / Ingestion
        gemini_model=_env_str("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        mlx_model_path=_env_str("MLX_GLM_OCR_MODEL", "mlx-community/GLM-OCR-6bit"),
        ocr_min_dim=_env_int("OCR_MIN_DIM", 1200),
        ocr_max_dim=_env_int("OCR_MAX_DIM", 2400),
        default_ocr_mode=_env_str("RR_OCR_MODE", "Hybrid"),
        default_dpi=_env_int("RR_DPI", 150),
        # Chunking
        default_chunk_max_words=_env_int("RR_CHUNK_MAX_WORDS", 220),
        default_chunk_overlap_words=_env_int("RR_CHUNK_OVERLAP_WORDS", 40),
        # BM25
        default_bm25_k1=_env_float("RR_BM25_K1", 1.5),
        default_bm25_b=_env_float("RR_BM25_B", 0.75),
        # Dense
        default_dense_dimensions=_env_int("RR_DENSE_DIMENSIONS", 384),
        # Late interaction
        default_late_dimensions=_env_int("RR_LATE_DIMENSIONS", 128),
        default_late_max_doc_tokens=_env_int("RR_LATE_MAX_DOC_TOKENS", 256),
        # Visual
        default_visual_dimensions=_env_int("RR_VISUAL_DIMENSIONS", 384),
        default_visual_backend=_env_str("RR_VISUAL_BACKEND", "baseline"),
        default_visual_compression=_env_str("RR_VISUAL_COMPRESSION", "none"),
        # ColPali
        default_colpali_model=_env_str("RR_COLPALI_MODEL", "vidore/colpali-v1.2"),
        default_device=_env_str("RR_DEVICE", "auto"),
        # Retrieval
        default_top_k=_env_int("RR_TOP_K", 5),
        default_retrieval_mode=_env_str("RR_RETRIEVAL_MODE", "planner"),
        default_planner_merge_strategy=_env_str("RR_PLANNER_MERGE_STRATEGY", "score_max"),
        default_planner_rerank=_env_bool("RR_PLANNER_RERANK", True),
        default_route_vote_bonus=_env_float("RR_ROUTE_VOTE_BONUS", 0.08),
        default_rerank_overlap_weight=_env_float("RR_RERANK_OVERLAP_WEIGHT", 0.10),
    )


def reset_settings_cache_for_tests() -> None:
    get_settings.cache_clear()
