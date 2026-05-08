from __future__ import annotations

from typing import Any, Callable, Tuple

from PIL import Image

from core_processor.settings import MLX_MODEL_PATH

_mlx_model = None
_mlx_processor = None
_mlx_config = None
_mlx_generate: Any = None
_mlx_apply_chat_template: Any = None


def _get_mlx_model() -> Tuple[Any, Any, Any, Callable[..., Any], Callable[..., Any]]:
    global _mlx_model, _mlx_processor, _mlx_config, _mlx_generate, _mlx_apply_chat_template
    if _mlx_model is None or _mlx_processor is None or _mlx_config is None:
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config

        # Downloads on first run. Keep this lazy so CLI/schema tests and cloud-only
        # flows do not pay the local model startup cost at import time.
        print(f"Loading {MLX_MODEL_PATH} via MLX...")
        _mlx_model, _mlx_processor = load(MLX_MODEL_PATH)
        _mlx_config = load_config(MLX_MODEL_PATH)
        _mlx_generate = generate
        _mlx_apply_chat_template = apply_chat_template
        print("MLX model ready.")
    return _mlx_model, _mlx_processor, _mlx_config, _mlx_generate, _mlx_apply_chat_template


def glm_ocr_mlx(img: Image.Image, system_prompt: str, user_query: str) -> str:
    model, processor, config, generate, apply_chat_template = _get_mlx_model()
    prompt = apply_chat_template(
        processor,
        config,
        system_prompt + "\n\n" + user_query,
        num_images=1,
    )
    result = generate(model, processor, prompt, img, max_tokens=4096, verbose=False)
    return result.text if hasattr(result, "text") else str(result)
