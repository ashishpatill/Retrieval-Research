from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval_research.chunking import chunk_document
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import build_indexes
from retrieval_research.storage import ArtifactStore


GENERATED_DIR = ROOT / "data" / "generated" / "phase4_visual_fixture"
MANIFEST_PATH = ROOT / "data" / "generated" / "phase4_visual_eval.local.json"


def _draw_table(path: Path) -> None:
    image = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(image)
    # Dense line structure to represent table-like pages.
    for x in range(80, 920, 120):
        draw.line((x, 80, x, 620), fill="black", width=4)
    for y in range(80, 640, 70):
        draw.line((80, y, 920, y), fill="black", width=4)
    image.save(path, format="PNG")


def _draw_diagram(path: Path) -> None:
    image = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((120, 180, 380, 440), outline="black", width=8)
    draw.rectangle((620, 180, 900, 440), outline="black", width=8)
    draw.line((380, 310, 620, 310), fill="black", width=8)
    draw.polygon([(580, 290), (620, 310), (580, 330)], fill="black")
    draw.line((250, 120, 250, 180), fill="black", width=8)
    draw.line((750, 440, 750, 560), fill="black", width=8)
    image.save(path, format="PNG")


def _build_manifest(document_ids: List[str]) -> Dict[str, Any]:
    table_doc, diagram_doc = document_ids
    return {
        "document_ids": document_ids,
        "queries": [
            {
                "query": "Which page looks like a table with rows and columns?",
                "document_id": table_doc,
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Find the page with a flow diagram and connecting arrow.",
                "document_id": diagram_doc,
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Locate the table visual layout page in this corpus.",
                "document_ids": document_ids,
                "expected_pages": [1],
                "expected_terms": [],
            },
        ],
    }


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    table_path = GENERATED_DIR / "table_layout.png"
    diagram_path = GENERATED_DIR / "diagram_layout.png"
    _draw_table(table_path)
    _draw_diagram(diagram_path)

    store = ArtifactStore(str(ROOT / "data"))
    document_ids: List[str] = []
    for source in (table_path, diagram_path):
        document = ingest_path(str(source), store=store, run_ocr=False)
        chunks = chunk_document(document, max_words=40, overlap_words=0)
        store.save_chunks(document.id, chunks)
        build_indexes(store, document.id, mode="all")
        document_ids.append(document.id)
        print(f"{source.name}: {document.id}")

    manifest = _build_manifest(document_ids)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"run: python3 -m retrieval_research.cli eval {MANIFEST_PATH.relative_to(ROOT)} --modes visual planner")


if __name__ == "__main__":
    main()
