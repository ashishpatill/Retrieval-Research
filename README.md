# 🧠 Retrieval-Research
Ideating, experimenting, optimising and testing Retrieval

**State-of-the-Art 2026 Document Parser** — GLM-OCR (local) + Gemini 3.1 Pro Preview (`gemini-3.1-pro-preview`)

Features:
- Batch processing (100+ pages)
- Streamlit + Gradio interfaces
- Pure Local / Pure Gemini / Hybrid mode
- History + ZIP export
- v0.1 retrieval pipeline: canonical artifacts, page-aware chunks, BM25 indexing, query traces

## Quick Start
```bash
ollama pull glm-ocr
pip install -r requirements.txt
# Add GEMINI_API_KEY to .env
streamlit run streamlit_app.py
# or
python gradio_app.py
```

## Retrieval v0.1 CLI

The CLI stores artifacts under `data/` and can ingest text/Markdown, prior history JSON, images, and PDFs. Image/PDF OCR is opt-in because local OCR model startup is expensive.

```bash
python3 -m retrieval_research.cli ingest README.md
python3 -m retrieval_research.cli chunk <document-id>
python3 -m retrieval_research.cli index <document-id> --mode all
python3 -m retrieval_research.cli query "retrieval pipeline" --mode planner
python3 -m retrieval_research.cli eval datasets/manifests/readme_eval.example.json
```

For PDFs/images with OCR:

```bash
python3 -m retrieval_research.cli ingest path/to/file.pdf --ocr --mode Hybrid --dpi 150
```

For real visual page retrieval with ColPali, install the optional runtime and rebuild the visual index:

```bash
pip install colpali-engine torch
python3 -m retrieval_research.cli index <document-id> --mode visual --visual-backend colpali --device auto
python3 -m retrieval_research.cli query "what does the diagram show?" --document-id <document-id> --mode visual
```

The default visual backend remains `baseline` so the project runs without GPU/model downloads.

Generated query runs include:

- `data/runs/<run-id>/evidence_bundle.json`
- `data/runs/<run-id>/retrieval_trace.json`
- `data/runs/<run-id>/eval_report.json`
- `data/runs/<run-id>/eval_report.md`

See `IMPLEMENTATION_PLAN.md` for the phased build plan.
