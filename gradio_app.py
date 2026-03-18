import gradio as gr
from pdf2image import convert_from_bytes
from core_processor import process_page
from PIL import Image
import io, zipfile, base64
import json
from datetime import datetime

def process_batch(files, mode, system_prompt, user_query):
    results = []
    progress = gr.Progress()
    total_pages = 0
    # count pages...
    for i, file in enumerate(files):
        # same PDF/image handling
        # call process_page for each page
        # collect results
        progress((i+1)/len(files))
    # return zipped results + markdown view
    return "Batch complete! Download ZIP below.", zip_buffer.getvalue()

# Gradio UI with tabs, dropdown for mode, batch file uploader, progress
with gr.Blocks(title="GLM-OCR + Gemini 3.1 Pro") as demo:
    # ... full beautiful Gradio interface with live preview
demo.launch()
