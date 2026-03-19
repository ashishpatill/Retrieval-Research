import gradio as gr
from pdf2image import convert_from_bytes
from core_processor import process_page, GEMINI_MODEL
from PIL import Image
import io
import zipfile
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

MODE_MAP = {
    "Pure Local (GLM-OCR)": "Pure Local",
    f"Pure Cloud ({GEMINI_MODEL})": "Pure Cloud",
    "Hybrid (Recommended)": "Hybrid",
}


def process_batch(files, mode_label, system_prompt, user_query, progress=gr.Progress()):
    if not files:
        return "No files uploaded.", None

    proc_mode = MODE_MAP.get(mode_label, "Hybrid")
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_data = {"timestamp": job_id, "mode": mode_label, "results": []}

    zip_buf = io.BytesIO()
    md_output = []
    all_pages = []

    # Collect all pages first for progress tracking
    for file in files:
        file_bytes = open(file.name, "rb").read() if hasattr(file, "name") else file
        fname = os.path.basename(file.name) if hasattr(file, "name") else "file"
        if fname.lower().endswith(".pdf"):
            images = convert_from_bytes(file_bytes, dpi=300)
        else:
            images = [Image.open(io.BytesIO(file_bytes))]
        all_pages.append((fname, file_bytes, images))

    total = sum(len(imgs) for _, _, imgs in all_pages)
    done = 0

    with zipfile.ZipFile(zip_buf, "w") as zf:
        for fname, _, images in all_pages:
            file_results = []
            md_output.append(f"## {fname}\n")

            for page_num, img in enumerate(images, 1):
                progress(done / total, desc=f"{fname} — page {page_num}/{len(images)}")
                glm_out, final_out = process_page(img, proc_mode, system_prompt, user_query)
                file_results.append({"page": page_num, "glm": glm_out, "final": final_out})

                stem = fname.rsplit(".", 1)[0]
                zf.writestr(f"{stem}_page{page_num}.md", final_out)
                md_output.append(f"### Page {page_num}\n{final_out}\n")
                done += 1

            job_data["results"].append({"filename": fname, "pages": file_results})

    with open(f"{HISTORY_DIR}/{job_id}.json", "w") as f:
        json.dump(job_data, f, indent=2)

    zip_buf.seek(0)
    zip_path = f"/tmp/results_{job_id}.zip"
    with open(zip_path, "wb") as f:
        f.write(zip_buf.getvalue())

    return "\n".join(md_output), zip_path


DEFAULT_SYSTEM = "You are an expert document parser. Extract content accurately and preserve structure."
DEFAULT_QUERY = "Extract all text, tables as Markdown, formulas as LaTeX. Return clean structured output."

with gr.Blocks(title="GLM-OCR + Gemini") as demo:
    gr.Markdown(f"# 🧠 GLM-OCR + Gemini Hybrid Parser\nLocal OCR + Cloud Reasoning ({GEMINI_MODEL})")

    with gr.Row():
        with gr.Column(scale=1):
            files = gr.File(label="Upload PDFs / Images", file_count="multiple", file_types=[".pdf", ".png", ".jpg", ".jpeg"])
            mode = gr.Radio(
                list(MODE_MAP.keys()),
                value="Hybrid (Recommended)",
                label="Processing Mode",
            )
            system_prompt = gr.Textbox(label="System Prompt", value=DEFAULT_SYSTEM, lines=3)
            user_query = gr.Textbox(label="Instructions", value=DEFAULT_QUERY, lines=4)
            run_btn = gr.Button("🚀 Process", variant="primary")

        with gr.Column(scale=2):
            output_md = gr.Markdown(label="Results Preview")
            zip_file = gr.File(label="Download ZIP")

    run_btn.click(
        fn=process_batch,
        inputs=[files, mode, system_prompt, user_query],
        outputs=[output_md, zip_file],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
