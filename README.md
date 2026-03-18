# 🧠 Retrieval-Research
Ideating, experimenting, optimising and testing Retrieval

**State-of-the-Art 2026 Document Parser** — GLM-OCR (local) + Gemini 3.1 Pro Preview (`gemini-3.1-pro-preview`)

Features:
- Batch processing (100+ pages)
- Streamlit + Gradio interfaces
- Pure Local / Pure Gemini / Hybrid mode
- History + ZIP export

## Quick Start
```bash
ollama pull glm-ocr
pip install -r requirements.txt
# Add GEMINI_API_KEY to .env
streamlit run streamlit_app.py
# or
python gradio_app.py
