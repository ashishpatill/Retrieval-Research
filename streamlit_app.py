import streamlit as st
from pdf2image import convert_from_bytes
from core_processor import process_page, GEMINI_MODEL
from PIL import Image
import base64
import io
import json
import os
from datetime import datetime
import zipfile
from dotenv import load_dotenv
from retrieval_research.chunking import chunk_document
from retrieval_research.evidence import build_knowledge_card
from retrieval_research.retrieval import build_indexes, search_document
from retrieval_research.storage import ArtifactStore

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

st.set_page_config(page_title="GLM-OCR + Gemini", layout="wide", page_icon="🧠")
st.title("🧠 GLM-OCR + Gemini Hybrid Parser")
st.caption(f"Local OCR (GLM-OCR via Ollama) + Cloud Reasoning ({GEMINI_MODEL})")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    dpi = st.slider("PDF DPI (lower = faster)", min_value=72, max_value=300, value=150, step=1)
    mode = st.radio(
        "Processing Mode",
        ["Pure Local (GLM-OCR)", f"Pure Cloud ({GEMINI_MODEL})", "Hybrid (Recommended)"],
        index=2,
    )
    system_prompt = st.text_area(
        "System Prompt",
        value="You are an expert document parser. Extract content accurately and preserve structure.",
        height=100,
    )
    if "Cloud" in mode or "Hybrid" in mode:
        if not gemini_key:
            st.error("Add GEMINI_API_KEY to .env")
        else:
            st.success(f"Gemini ready ({GEMINI_MODEL})")
    st.info("Hybrid: GLM-OCR does raw extraction → Gemini refines with reasoning")

# Main UI
col1, col2 = st.columns([1, 1])
with col1:
    uploaded_files = st.file_uploader(
        "Upload PDFs/Images",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
with col2:
    user_query = st.text_area(
        "Your Instructions",
        value="Extract all text, tables as Markdown, formulas as LaTeX. Return clean structured output.",
        height=120,
    )

process_btn = st.button("🚀 Process", type="primary", use_container_width=True)

if process_btn and uploaded_files:
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_data = {"timestamp": job_id, "mode": mode, "results": []}

    # Map UI label to internal mode key
    if "Pure Local" in mode:
        proc_mode = "Pure Local"
    elif "Pure Cloud" in mode:
        proc_mode = "Pure Cloud"
    else:
        proc_mode = "Hybrid"

    # Pre-load all pages so we know total count
    all_file_images = []
    for file in uploaded_files:
        if file.type == "application/pdf":
            imgs = convert_from_bytes(file.getvalue(), dpi=dpi)
        else:
            imgs = [Image.open(io.BytesIO(file.getvalue()))]
        all_file_images.append((file.name, imgs))

    total_pages = sum(len(imgs) for _, imgs in all_file_images)
    progress_bar = st.progress(0, text="Starting...")
    done = 0

    with st.status("Processing...") as status:
        for fname, images in all_file_images:
            file_results = []
            for page_num, img in enumerate(images, 1):
                label = f"📄 {fname} — page {page_num}/{len(images)}"
                status.update(label=label)
                progress_bar.progress(done / total_pages, text=label)
                glm_out, final_out = process_page(img, proc_mode, system_prompt, user_query)
                file_results.append({"page": page_num, "glm": glm_out, "final": final_out})
                done += 1
                progress_bar.progress(done / total_pages, text=f"✅ {label}")

            job_data["results"].append({"filename": fname, "pages": file_results})

    with open(f"{HISTORY_DIR}/{job_id}.json", "w") as f:
        json.dump(job_data, f, indent=2)

    status.update(label="✅ Complete!", state="complete")
    progress_bar.progress(1.0, text="✅ All pages processed!")
    st.success(f"Job {job_id} saved!")

# ── History ──────────────────────────────────────────────────────────────────
st.divider()
st.header("📖 Processing History")

history_files = sorted(
    [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True
)

if not history_files:
    st.info("No jobs yet. Upload files and click Process.")
else:
    selected_job = st.selectbox(
        "Select job",
        history_files,
        format_func=lambda f: f.replace(".json", ""),
    )

    try:
        with open(f"{HISTORY_DIR}/{selected_job}") as f:
            job = json.load(f)
    except (json.JSONDecodeError, ValueError):
        st.error(f"Corrupted history file: {selected_job}. Delete it and re-run.")
        st.stop()

    st.caption(f"Mode: **{job.get('mode', 'N/A')}** | Timestamp: {job.get('timestamp', '')}")
    is_hybrid = "Hybrid" in job.get("mode", "")

    # ZIP download
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for file_data in job["results"]:
            for pg in file_data["pages"]:
                name = file_data["filename"].rsplit(".", 1)[0]
                zf.writestr(f"{name}_page{pg['page']}.md", pg["final"])
    zip_buf.seek(0)
    st.download_button(
        "⬇️ Download all results as ZIP",
        data=zip_buf,
        file_name=f"results_{job.get('timestamp', 'job')}.zip",
        mime="application/zip",
    )

    for file_data in job["results"]:
        st.subheader(f"📄 {file_data['filename']}")
        for pg in file_data["pages"]:
            with st.expander(f"Page {pg['page']}", expanded=len(file_data["pages"]) == 1):
                if is_hybrid:
                    tab_glm, tab_final, tab_diff = st.tabs(["GLM Raw", "Gemini Final", "Side-by-side"])
                    with tab_glm:
                        st.markdown(pg.get("glm", ""), unsafe_allow_html=False)
                    with tab_final:
                        st.markdown(pg.get("final", ""), unsafe_allow_html=False)
                    with tab_diff:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption("GLM-OCR Raw")
                            st.text_area("GLM raw text", value=pg.get("glm", ""), height=400, key=f"glm_{file_data['filename']}_{pg['page']}", label_visibility="collapsed")
                        with c2:
                            st.caption("Gemini Final")
                            st.text_area("Gemini final text", value=pg.get("final", ""), height=400, key=f"final_{file_data['filename']}_{pg['page']}", label_visibility="collapsed")
                else:
                    st.markdown(pg.get("final", ""), unsafe_allow_html=False)

# ── Retrieval Inspector ─────────────────────────────────────────────────────
st.divider()
st.header("🔎 Retrieval Inspector")

store = ArtifactStore("data")
documents = store.list_documents()

if not documents:
    st.info("No indexed documents yet. Use `python3 -m retrieval_research.cli ingest <path>` to add one.")
else:
    doc_options = {f"{doc.title} ({doc.id})": doc for doc in documents}
    selected_label = st.selectbox("Document", list(doc_options.keys()))
    selected_doc = doc_options[selected_label]

    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
    with metric_col1:
        st.metric("Pages", len(selected_doc.pages))
    with metric_col2:
        try:
            chunks = store.load_chunks(selected_doc.id)
        except FileNotFoundError:
            chunks = []
        st.metric("Chunks", len(chunks))
    with metric_col3:
        try:
            store.load_index(selected_doc.id, "bm25")
            bm25_ready = True
        except FileNotFoundError:
            bm25_ready = False
        st.metric("BM25 Index", "Ready" if bm25_ready else "Missing")
    with metric_col4:
        try:
            store.load_index(selected_doc.id, "dense")
            dense_ready = True
        except FileNotFoundError:
            dense_ready = False
        st.metric("Dense Index", "Ready" if dense_ready else "Missing")
    with metric_col5:
        try:
            store.load_index(selected_doc.id, "late")
            late_ready = True
        except FileNotFoundError:
            late_ready = False
        st.metric("Late Index", "Ready" if late_ready else "Missing")
    with metric_col6:
        try:
            store.load_index(selected_doc.id, "visual")
            visual_ready = True
        except FileNotFoundError:
            visual_ready = False
        st.metric("Visual Index", "Ready" if visual_ready else "Missing")

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("Build chunks", use_container_width=True):
            chunks = chunk_document(selected_doc)
            store.save_chunks(selected_doc.id, chunks)
            st.success(f"Saved {len(chunks)} chunks.")
            st.rerun()
    with action_col2:
        visual_backend = st.selectbox("Visual backend", ["baseline", "colpali"])
        visual_compression = st.selectbox("Visual compression", ["none", "int8"])
        colpali_model = st.text_input("ColPali model", value="vidore/colpali-v1.2")
        if st.button("Build indexes", use_container_width=True):
            try:
                paths = build_indexes(
                    store,
                    selected_doc.id,
                    mode="all",
                    visual_backend=visual_backend,
                    colpali_model=colpali_model,
                    visual_compression=visual_compression,
                )
                st.success(f"Saved {len(paths)} indexes.")
                st.rerun()
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))

    query = st.text_input("Ask a question about this document")
    retrieval_mode = st.radio("Retrieval mode", ["planner", "hybrid", "bm25", "dense", "late", "visual", "graph"], horizontal=True)
    top_k = st.slider("Top K", min_value=1, max_value=10, value=5)
    if query:
        try:
            evidence, steps = search_document(store, selected_doc.id, query, mode=retrieval_mode, top_k=top_k)
            knowledge_card = build_knowledge_card(query, evidence)
            st.markdown("### Answer")
            st.text(knowledge_card.answer)
            with st.expander("Knowledge card"):
                st.json(knowledge_card.to_dict())
            with st.expander("Retrieval trace"):
                st.json({"mode": retrieval_mode, "steps": steps})
            st.markdown("### Evidence")
            for item in evidence:
                label = f"{item.chunk_id} | {item.retrieval_path} | score {item.score:.3f} | pages {item.page_numbers}"
                with st.expander(label):
                    st.write(item.text)
        except FileNotFoundError:
            st.warning("Build chunks and indexes before querying this document.")
