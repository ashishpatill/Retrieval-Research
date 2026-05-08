from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval_research.chunking import chunk_document
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import build_indexes
from retrieval_research.storage import ArtifactStore


GENERATED_DIR = ROOT / "data" / "generated" / "visual_broad_benchmark"
MANIFEST_PATH = ROOT / "data" / "generated" / "visual_broad_benchmark_eval.json"


def _draw_dense_table(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    cols = [80, 260, 440, 620, 800, 920]
    rows = [60, 120, 180, 240, 300, 360, 420, 480, 540, 600, 660]
    for x in cols:
        draw.line((x, 40, x, 720), fill="black", width=2)
    for y in rows:
        draw.line((80, y, 920, y), fill="black", width=2)
    draw.rectangle((78, 38, 922, 122), fill="lightgray", outline="black", width=2)
    labels = ["Name", "Revenue", "Growth", "Employees", "Region"]
    for i, label in enumerate(labels):
        cx = (cols[i] + cols[i + 1]) // 2
        draw.text((cx - 20, 75), label, fill="black")
    data = [
        ["Acme Corp", "$2.4B", "12.3%", "12,400", "NA"],
        ["Beta Inc", "$1.1B", "8.7%", "8,200", "EMEA"],
        ["Gamma LLC", "$890M", "15.2%", "5,100", "APAC"],
        ["Delta Co", "$3.2B", "5.1%", "18,900", "NA"],
        ["Epsilon SA", "$650M", "22.8%", "3,400", "EMEA"],
        ["Zeta KG", "$1.8B", "10.4%", "9,800", "APAC"],
        ["Eta Ltd", "$420M", "18.9%", "2,100", "LATAM"],
        ["Theta NV", "$5.1B", "3.2%", "24,500", "NA"],
        ["Iota AB", "$2.9B", "9.6%", "11,200", "EMEA"],
    ]
    for ri, row in enumerate(data):
        for ci in range(len(labels)):
            cx = (cols[ci] + cols[ci + 1]) // 2
            cy = rows[ri + 1] + 30
            draw.text((cx - 25, cy), row[ci], fill="black")
    img.save(path, format="PNG")


def _draw_form_layout(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 960, 100), fill="navy", outline="black", width=2)
    draw.text((300, 55), "APPLICATION FORM - EMPLOYMENT", fill="white")
    fields = [
        ("Full Name:", (60, 140), (300, 180)),
        ("Date of Birth:", (60, 210), (300, 250)),
        ("Email Address:", (60, 280), (600, 320)),
        ("Phone Number:", (60, 350), (400, 390)),
        ("Current Employer:", (60, 420), (500, 460)),
        ("Years of Experience:", (60, 490), (350, 530)),
        ("Education Level:", (60, 560), (350, 600)),
        ("Position Applied:", (60, 630), (500, 670)),
    ]
    for label, tl, br in fields:
        draw.text(tl, label, fill="black")
        draw.rectangle((tl[0] + 180, tl[1], br[0], br[1]), outline="black", width=1)
    draw.rectangle((60, 700, 140, 730), outline="black", width=2)
    draw.line((75, 715, 125, 715), fill="black", width=2)
    draw.text((150, 700), "I agree to the terms and conditions", fill="black")
    draw.rectangle((60, 750, 200, 780), fill="navy", outline="black", width=2)
    draw.text((100, 755), "SUBMIT", fill="white")
    img.save(path, format="PNG")


def _draw_text_with_figure(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    paragraphs = [
        "1. Introduction",
        "The experimental results demonstrate a statistically significant improvement in",
        "retrieval quality when using the proposed multi-modal fusion approach. Our method",
        "combines visual layout features with traditional lexical signals to achieve a 23%",
        "relative improvement in mean reciprocal rank over the BM25 baseline.",
        "",
        "2. Methodology",
        "We evaluated our approach on a corpus of 1,200 document pages spanning research",
        "articles, technical reports, and financial statements. Each page was processed through",
        "our visual profiling pipeline which extracts layout orientation, texture, contrast,",
        "line density, and brightness features at 384 dimensions per page.",
        "",
        "3. Results",
        "Table 1 summarizes the retrieval performance across all tested configurations.",
        "The hybrid visual-lexical approach consistently outperformed single-modality",
        "baselines, particularly for pages with dense tabular content or complex layouts.",
    ]
    y = 50
    for line in paragraphs:
        draw.text((60, y), line, fill="black")
        y += 28
    draw.rectangle((600, 50, 940, 350), outline="black", width=2)
    draw.text((620, 300), "Figure 1: Architecture diagram", fill="black")
    draw.ellipse((640, 80, 780, 200), outline="black", width=3)
    draw.rectangle((800, 100, 920, 180), outline="black", width=3)
    draw.line((780, 140, 800, 140), fill="black", width=3)
    draw.line((720, 200, 720, 250), fill="black", width=3)
    draw.rectangle((660, 250, 780, 300), outline="black", width=2)
    img.save(path, format="PNG")


def _draw_bar_chart(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    draw.text((350, 30), "Quarterly Revenue by Region (2024)", fill="black")
    draw.line((120, 100, 120, 700), fill="black", width=2)
    draw.line((120, 700, 950, 700), fill="black", width=2)
    bars = [
        ("Q1", 180, 320, 250, 400),
        ("Q2", 250, 450, 320, 550),
        ("Q3", 320, 380, 390, 480),
        ("Q4", 390, 520, 460, 620),
    ]
    colors = ["coral", "steelblue", "seagreen", "goldenrod"]
    for (label, x1, h1, x2, h2), color in zip(bars, colors):
        draw.rectangle((x1 + 5, 700 - h1, x1 + 50, 700), fill=color, outline="black", width=1)
        draw.rectangle((x2 + 5, 700 - h2, x2 + 50, 700), fill=color, outline="black", width=1)
        draw.text((x1 + 5, 710), label, fill="black")
    draw.text((140, 680 - 400), "NA", fill="black")
    draw.text((310, 680 - 550), "EMEA", fill="black")
    draw.text((30, 100), "Revenue ($M)", fill="black")
    for val, y in [(100, 700), (200, 600), (300, 500), (400, 400), (500, 300), (600, 200)]:
        draw.text((10, y - 5), str(val), fill="black")
        draw.line((120, y, 130, y), fill="black", width=1)
    img.save(path, format="PNG")


def _draw_pie_chart(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    draw.text((350, 30), "Market Share by Vendor", fill="black")
    wedges = [
        ((150, 80, 650, 580), -30, 100, "coral"),
        ((150, 80, 650, 580), 70, 80, "steelblue"),
        ((150, 80, 650, 580), 150, 60, "seagreen"),
        ((150, 80, 650, 580), 210, 50, "goldenrod"),
        ((150, 80, 650, 580), 260, 70, "mediumpurple"),
    ]
    for box, start, end, color in wedges:
        draw.pieslice(box, start, start + end, fill=color, outline="black", width=2)
    legend = [("Vendor A - 28%", "coral"), ("Vendor B - 22%", "steelblue"),
              ("Vendor C - 17%", "seagreen"), ("Vendor D - 14%", "goldenrod"),
              ("Vendor E - 19%", "mediumpurple")]
    for i, (label, color) in enumerate(legend):
        draw.rectangle((750, 100 + i * 40, 780, 120 + i * 40), fill=color, outline="black", width=1)
        draw.text((790, 100 + i * 40), label, fill="black")
    img.save(path, format="PNG")


def _draw_sparse_table(path: Path) -> None:
    img = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(img)
    draw.text((300, 30), "Key Financial Metrics", fill="black")
    draw.text((80, 80), "Metric", fill="black")
    draw.text((500, 80), "Value", fill="black")
    draw.text((700, 80), "Change", fill="black")
    metrics = [
        ("Gross Profit Margin", "68.4%", "+2.1pp"),
        ("Operating Margin", "24.7%", "-0.8pp"),
        ("Net Profit Margin", "18.2%", "+1.5pp"),
        ("Return on Equity", "32.5%", "+4.2pp"),
        ("Current Ratio", "2.1x", "-0.3x"),
        ("Debt-to-Equity", "0.45x", "-0.08x"),
        ("Free Cash Flow", "$420M", "+$85M"),
        ("Earnings Per Share", "$4.82", "+$0.54"),
    ]
    y = 120
    for metric, val, change in metrics:
        draw.line((60, y, 940, y), fill="lightgray", width=1)
        draw.text((80, y + 5), metric, fill="black")
        draw.text((500, y + 5), val, fill="black")
        draw.text((700, y + 5), change, fill="black")
        y += 45
    draw.line((60, y, 940, y), fill="black", width=2)
    img.save(path, format="PNG")


FIXTURES: List[Tuple[str, Any]] = [
    ("dense_table", _draw_dense_table),
    ("application_form", _draw_form_layout),
    ("text_with_figure", _draw_text_with_figure),
    ("bar_chart", _draw_bar_chart),
    ("pie_chart", _draw_pie_chart),
    ("financial_metrics", _draw_sparse_table),
]


def _build_manifest(doc_ids: List[str]) -> Dict[str, Any]:
    id_map = dict(zip([name for name, _ in FIXTURES], doc_ids))
    return {
        "document_ids": doc_ids,
        "queries": [
            {
                "query": "Which page shows a dense data table with company revenue and employee counts?",
                "document_id": id_map["dense_table"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Find the employment application form page with signature and submit button.",
                "document_id": id_map["application_form"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Locate the page that contains a research article with an embedded architecture figure.",
                "document_id": id_map["text_with_figure"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Which page displays a bar chart comparing quarterly revenue across regions?",
                "document_id": id_map["bar_chart"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Find the pie chart page showing market share distribution among vendors.",
                "document_id": id_map["pie_chart"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Which page has a sparse financial metrics table with profit margins and ratios?",
                "document_id": id_map["financial_metrics"],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Find pages containing structured tabular data with rows and columns.",
                "document_ids": [id_map["dense_table"], id_map["financial_metrics"]],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Locate pages with chart or diagram visualizations.",
                "document_ids": [id_map["bar_chart"], id_map["pie_chart"], id_map["text_with_figure"]],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Which pages contain form-like layouts with labeled fields?",
                "document_ids": [id_map["application_form"]],
                "expected_pages": [1],
                "expected_terms": [],
            },
            {
                "query": "Find all pages that would benefit from visual layout analysis over pure text retrieval.",
                "document_ids": doc_ids,
                "expected_pages": [1],
                "expected_terms": [],
            },
        ],
    }


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for name, drawer in FIXTURES:
        path = GENERATED_DIR / f"{name}.png"
        drawer(path)
        image_paths.append(path)
        print(f"drawn: {path.name}")

    store = ArtifactStore(str(ROOT / "data"))
    doc_ids: List[str] = []
    for source in image_paths:
        doc = ingest_path(str(source), store=store, run_ocr=False)
        chunks = chunk_document(doc, max_words=40, overlap_words=0)
        store.save_chunks(doc.id, chunks)
        build_indexes(store, doc.id, mode="all")
        doc_ids.append(doc.id)
        print(f"{source.name}: {doc.id}")

    manifest = _build_manifest(doc_ids)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nmanifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"docs: {len(doc_ids)}, queries: {len(manifest['queries'])}")
    print(f"\nrun: python3 -m retrieval_research.cli eval {MANIFEST_PATH.relative_to(ROOT)} --modes visual planner")


if __name__ == "__main__":
    main()
