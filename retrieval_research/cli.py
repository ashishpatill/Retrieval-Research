from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from retrieval_research.chunking import chunk_document
from retrieval_research.evidence import build_knowledge_card
from retrieval_research.evaluation.runner import report_to_markdown, run_eval
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import DEFAULT_COLPALI_MODEL, RETRIEVAL_MODES, build_indexes, search_corpus
from retrieval_research.schema import RetrievalResult, RetrievalTrace
from retrieval_research.storage import ArtifactStore


def _store(args: argparse.Namespace) -> ArtifactStore:
    return ArtifactStore(args.store)


def cmd_ingest(args: argparse.Namespace) -> None:
    document = ingest_path(
        args.path,
        store=_store(args),
        run_ocr=args.ocr,
        mode=args.mode,
        dpi=args.dpi,
    )
    print(document.id)
    print(f"saved: {Path(args.store) / 'processed' / document.id / 'document.json'}")


def cmd_chunk(args: argparse.Namespace) -> None:
    store = _store(args)
    document = store.load_document(args.document_id)
    chunks = chunk_document(document, max_words=args.max_words, overlap_words=args.overlap_words)
    path = store.save_chunks(document.id, chunks)
    print(f"chunks: {len(chunks)}")
    print(f"saved: {path}")


def cmd_index(args: argparse.Namespace) -> None:
    store = _store(args)
    chunks = store.load_chunks(args.document_id)
    try:
        paths = build_indexes(
            store,
            args.document_id,
            mode=args.mode,
            visual_backend=args.visual_backend,
            colpali_model=args.colpali_model,
            device=args.device,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    print(f"indexed chunks: {len(chunks)}")
    for path in paths:
        print(f"saved: {path}")


def _candidate_documents(store: ArtifactStore, document_id: Optional[str]) -> List[str]:
    if document_id:
        return [document_id]
    return [document.id for document in store.list_documents()]


def cmd_query(args: argparse.Namespace) -> None:
    store = _store(args)
    document_ids = _candidate_documents(store, args.document_id)
    evidence, steps = search_corpus(store, document_ids, args.question, mode=args.mode, top_k=args.top_k)
    knowledge_card = build_knowledge_card(args.question, evidence)
    result = RetrievalResult(
        query=args.question,
        evidence=evidence,
        answer=knowledge_card.answer,
        knowledge_card=knowledge_card,
    )
    trace = RetrievalTrace(
        query=args.question,
        mode=args.mode,
        document_ids=document_ids,
        steps=steps,
    )
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    store.save_run(run_id, "evidence_bundle.json", result.to_dict())
    store.save_run(run_id, "knowledge_card.json", knowledge_card.to_dict())
    store.save_run(run_id, "retrieval_trace.json", trace.to_dict())
    print(knowledge_card.answer)
    print("")
    print(f"run: {Path(args.store) / 'runs' / run_id}")


def cmd_eval(args: argparse.Namespace) -> None:
    store = _store(args)
    report = run_eval(args.manifest, store=store, top_k=args.top_k, modes=args.modes)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    json_path = store.save_run(run_id, "eval_report.json", report)
    md_path = Path(args.store) / "runs" / run_id / "eval_report.md"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(f"queries: {metrics['query_count']}")
    for mode, mode_metrics in metrics["modes"].items():
        print(
            f"{mode}: term_hit_rate={mode_metrics['term_hit_rate']:.3f} "
            f"page_hit_rate={mode_metrics['page_hit_rate']:.3f} "
            f"answerable_rate={mode_metrics['answerable_rate']:.3f} "
            f"mrr={mode_metrics['mrr']:.3f}"
        )
    planner_vs_static = metrics.get("planner_vs_static", {})
    if planner_vs_static.get("available"):
        print(planner_vs_static["summary"])
    print(f"saved: {json_path}")
    print(f"saved: {md_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rr", description="Retrieval Research local CLI")
    parser.add_argument("--store", default="data", help="Artifact store root")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a document into canonical JSON")
    ingest.add_argument("path")
    ingest.add_argument("--ocr", action="store_true", help="Run OCR/refinement for image and PDF inputs")
    ingest.add_argument("--mode", choices=["Pure Local", "Pure Cloud", "Hybrid"], default="Hybrid")
    ingest.add_argument("--dpi", type=int, default=150)
    ingest.set_defaults(func=cmd_ingest)

    chunk = sub.add_parser("chunk", help="Create page-aware chunks")
    chunk.add_argument("document_id")
    chunk.add_argument("--max-words", type=int, default=220)
    chunk.add_argument("--overlap-words", type=int, default=40)
    chunk.set_defaults(func=cmd_chunk)

    index = sub.add_parser("index", help="Build retrieval indexes")
    index.add_argument("document_id")
    index.add_argument("--mode", choices=["all", "bm25", "dense", "hybrid", "visual", "graph", "planner"], default="all")
    index.add_argument("--visual-backend", choices=["baseline", "colpali"], default="baseline")
    index.add_argument("--colpali-model", default=DEFAULT_COLPALI_MODEL)
    index.add_argument("--device", default="auto", help="ColPali device: auto, cpu, mps, cuda:0, etc.")
    index.set_defaults(func=cmd_index)

    query = sub.add_parser("query", help="Query indexed documents")
    query.add_argument("question")
    query.add_argument("--document-id")
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--mode", choices=RETRIEVAL_MODES, default="hybrid")
    query.set_defaults(func=cmd_query)

    eval_parser = sub.add_parser("eval", help="Run a retrieval eval manifest")
    eval_parser.add_argument("manifest")
    eval_parser.add_argument("--top-k", type=int, default=5)
    eval_parser.add_argument("--modes", nargs="+", choices=RETRIEVAL_MODES, default=["bm25", "dense", "hybrid", "planner"])
    eval_parser.set_defaults(func=cmd_eval)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
