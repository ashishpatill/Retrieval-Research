import io
import base64
import os
import numpy as np
import cv2
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None
GEMINI_MODEL = "gemini-3.1-pro-preview"

MLX_MODEL_PATH = "mlx-community/GLM-OCR-6bit"
OCR_MIN_DIM = 1200
OCR_MAX_DIM = 2400

_mlx_model = None
_mlx_processor = None
_mlx_config = None
_mlx_generate = None
_mlx_apply_chat_template = None


def _get_mlx_model():
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


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    tl, tr, br, bl = rect
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (width, height))


def _crop_document(img: Image.Image) -> Image.Image:
    orig = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    otsu_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges = cv2.Canny(blurred, otsu_thresh * 0.5, otsu_thresh)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    img_area = orig.shape[0] * orig.shape[1]
    doc_contour = None
    for c in contours[:10]:
        area = cv2.contourArea(c)
        if area < 0.15 * img_area or area > 0.98 * img_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx.reshape(4, 2).astype("float32")
            break
    if doc_contour is None:
        return img
    return Image.fromarray(_four_point_transform(orig, doc_contour))


def _resize_for_ocr(img: Image.Image) -> Image.Image:
    w, h = img.size
    long_side = max(w, h)
    if long_side <= OCR_MAX_DIM:
        return img
    scale = OCR_MAX_DIM / long_side
    new_w, new_h = int(w * scale), int(h * scale)
    if min(new_w, new_h) < OCR_MIN_DIM:
        scale = OCR_MIN_DIM / min(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _glm_ocr_mlx(img: Image.Image, system_prompt: str, user_query: str) -> str:
    model, processor, config, generate, apply_chat_template = _get_mlx_model()
    prompt = apply_chat_template(
        processor, config,
        system_prompt + "\n\n" + user_query,
        num_images=1,
    )
    result = generate(model, processor, prompt, img, max_tokens=4096, verbose=False)
    return result.text if hasattr(result, "text") else str(result)


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

    # GLM-OCR stage — native MLX on M1
    if mode in ["Pure Local", "Hybrid"]:
        print("[4/5] Running GLM-OCR via MLX...")
        glm_output = _glm_ocr_mlx(img, system_prompt, user_query)
        print(f"      GLM-OCR done — {len(glm_output)} chars")

    # Gemini stage
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
