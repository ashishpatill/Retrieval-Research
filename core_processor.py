import ollama
import google.generativeai as genai
from PIL import Image
import base64
import io
from dotenv import load_dotenv
import os

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    gemini_model = genai.GenerativeModel("gemini-3.1-pro-preview")
else:
    gemini_model = None

def process_page(img: Image, mode: str, system_prompt: str, user_query: str):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()

    glm_output = ""
    final_output = ""

    # GLM stage
    if mode in ["Pure Local", "Hybrid"]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query, "images": [img_b64]}
        ]
        glm_response = ollama.chat(model="glm-ocr", messages=messages)
        glm_output = glm_response['message']['content']

    # Gemini stage
    if mode in ["Pure Cloud", "Hybrid"] and gemini_model:
        parts = [system_prompt + "\n\n" + user_query]
        if mode == "Hybrid":
            parts.append(f"Refine this GLM-OCR output:\n{glm_output}")
        parts.append({"inline_data": {"mime_type": "image/png", "data": img_b64}})
        gemini_response = gemini_model.generate_content(parts)
        final_output = gemini_response.text
    else:
        final_output = glm_output

    return glm_output, final_output
