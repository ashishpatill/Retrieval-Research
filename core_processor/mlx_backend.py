from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple

from PIL import Image

from core_processor.settings import MLX_MODEL_PATH
from retrieval_research.log import get_logger

_logger = get_logger("core_processor.mlx")
_MLX_UNAVAILABLE: Optional[str] = None
_MLX_UNAVAILABLE_LOGGED: bool = False

_mlx_model = None
_mlx_processor = None
_mlx_config = None
_mlx_generate: Any = None
_mlx_apply_chat_template: Any = None


def is_mlx_available() -> bool:
    return _MLX_UNAVAILABLE is None and _mlx_model is not None


def _get_mlx_model() -> Tuple[Any, Any, Any, Callable[..., Any], Callable[..., Any]]:
    global _mlx_model, _mlx_processor, _mlx_config, _mlx_generate, _mlx_apply_chat_template, _MLX_UNAVAILABLE, _MLX_UNAVAILABLE_LOGGED
    if _MLX_UNAVAILABLE is not None:
        if not _MLX_UNAVAILABLE_LOGGED:
            _logger.warning(
                "MLX/GLM-OCR unavailable: %s — install with: pip install mlx-vlm",
                _MLX_UNAVAILABLE,
            )
            _MLX_UNAVAILABLE_LOGGED = True
        raise RuntimeError(f"MLX/GLM-OCR unavailable: {_MLX_UNAVAILABLE}")
    if _mlx_model is None or _mlx_processor is None or _mlx_config is None:
        try:
            from mlx_vlm import generate, load
            from mlx_vlm.prompt_utils import apply_chat_template
            from mlx_vlm.utils import load_config
        except ImportError as exc:
            _MLX_UNAVAILABLE = str(exc)
            _logger.warning(
                "MLX/GLM-OCR requires optional dependencies — install with: pip install mlx-vlm"
            )
            _MLX_UNAVAILABLE_LOGGED = True
            raise

        try:
            _logger.info("Loading %s via MLX...", MLX_MODEL_PATH)
            _mlx_model, _mlx_processor = load(MLX_MODEL_PATH)
            _mlx_config = load_config(MLX_MODEL_PATH)
            _mlx_generate = generate
            _mlx_apply_chat_template = apply_chat_template
            _logger.info("MLX model ready.")
        except Exception as exc:
            _MLX_UNAVAILABLE = str(exc)
            _logger.warning("Failed to load MLX model %s: %s", MLX_MODEL_PATH, exc)
            _MLX_UNAVAILABLE_LOGGED = True
            raise
    return _mlx_model, _mlx_processor, _mlx_config, _mlx_generate, _mlx_apply_chat_template


def glm_ocr_mlx(img: Image.Image, system_prompt: str, user_query: str) -> str:
    try:
        model, processor, config, generate, apply_chat_template = _get_mlx_model()
        prompt = apply_chat_template(
            processor,
            config,
            system_prompt + "\n\n" + user_query,
            num_images=1,
        )
        result = generate(model, processor, prompt, img, max_tokens=4096, verbose=False)
        return result.text if hasattr(result, "text") else str(result)
    except RuntimeError:
        return ""
    except Exception as exc:
        _logger.error("GLM-OCR generation failed: %s", exc)
        return ""
