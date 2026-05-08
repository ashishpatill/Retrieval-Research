from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple

from PIL import Image

from core_processor.settings import MLX_MODEL_PATH
from retrieval_research.log import get_logger

_logger = get_logger("core_processor.mlx")
_MLX_UNAVAILABLE: Optional[str] = None

_mlx_model = None
_mlx_processor = None
_mlx_config = None
_mlx_generate: Any = None
_mlx_apply_chat_template: Any = None


def _get_mlx_model() -> Tuple[Any, Any, Any, Callable[..., Any], Callable[..., Any]]:
    global _mlx_model, _mlx_processor, _mlx_config, _mlx_generate, _mlx_apply_chat_template, _MLX_UNAVAILABLE
    if _MLX_UNAVAILABLE is not None:
        raise RuntimeError(f"MLX/GLM-OCR unavailable: {_MLX_UNAVAILABLE}")
    if _mlx_model is None or _mlx_processor is None or _mlx_config is None:
        try:
            from mlx_vlm import generate, load
            from mlx_vlm.prompt_utils import apply_chat_template
            from mlx_vlm.utils import load_config
        except ImportError as exc:
            _MLX_UNAVAILABLE = str(exc)
            raise RuntimeError(
                "MLX/GLM-OCR requires optional dependencies. "
                "Install with: pip install mlx-vlm"
            ) from exc

        try:
            _logger.info("Loading %s via MLX...", MLX_MODEL_PATH)
            _mlx_model, _mlx_processor = load(MLX_MODEL_PATH)
            _mlx_config = load_config(MLX_MODEL_PATH)
            _mlx_generate = generate
            _mlx_apply_chat_template = apply_chat_template
            _logger.info("MLX model ready.")
        except Exception as exc:
            _MLX_UNAVAILABLE = str(exc)
            raise RuntimeError(f"Failed to load MLX model {MLX_MODEL_PATH}: {exc}") from exc
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
        raise
    except Exception as exc:
        _logger.error("GLM-OCR generation failed: %s", exc)
        return ""
