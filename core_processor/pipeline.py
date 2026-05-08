from __future__ import annotations

import io

from PIL import Image
from google.genai import types

from core_processor.gemini_client import get_gemini_client
from core_processor.image_geometry import _crop_document, _resize_for_ocr
from core_processor.mlx_backend import glm_ocr_mlx
from core_processor.settings import GEMINI_MODEL


def process_page(img: Image.Image, mode: str, system_prompt: str, user_query: str):
    print(f"[1/5] Crop document — input size: {img.size}")
    img = _crop_document(img)
    print(f"[2/5] Resize for OCR — size after crop: {img.size}")
    img = _resize_for_ocr(img)
    print(f"[3/5] Image ready — final size: {img.size}")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    print(f"      PNG size: {len(img_bytes) / 1024:.1f} KB")

    glm_output = ""
    final_output = ""

    if mode in ["Pure Local", "Hybrid"]:
        print("[4/5] Running GLM-OCR via MLX...")
        glm_output = glm_ocr_mlx(img, system_prompt, user_query)
        print(f"      GLM-OCR done — {len(glm_output)} chars")

    gemini_client = get_gemini_client()
    if mode in ["Pure Cloud", "Hybrid"] and gemini_client:
        if mode == "Hybrid":
            text = (
                f"{system_prompt}\n\n{user_query}\n\n"
                f"GLM-OCR raw output to refine:\n{glm_output}\n\n"
                "Improve structure, fix errors, and reason step-by-step."
            )
        else:
            text = f"{system_prompt}\n\n{user_query}"
        print(f"[5/5] Running Gemini ({GEMINI_MODEL})...")
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_text(text=text),
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            ],
        )
        final_output = response.text
        print(f"      Gemini done — {len(final_output)} chars")
    else:
        final_output = glm_output

    return glm_output, final_output
