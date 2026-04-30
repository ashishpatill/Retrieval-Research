from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

from retrieval_research.schema import Chunk, Document, DocumentProfile


class ArtifactStore:
    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.pages_dir = self.root / "pages"
        self.processed_dir = self.root / "processed"
        self.indexes_dir = self.root / "indexes"
        self.runs_dir = self.root / "runs"
        for path in [
            self.raw_dir,
            self.pages_dir,
            self.processed_dir,
            self.indexes_dir,
            self.runs_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def document_dir(self, document_id: str) -> Path:
        path = self.processed_dir / document_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def page_dir(self, document_id: str) -> Path:
        path = self.pages_dir / document_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def copy_raw(self, source: Path, document_id: str) -> str:
        target_dir = self.raw_dir / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        if source.exists() and source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return str(target)

    def save_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def save_document(self, document: Document) -> Path:
        path = self.document_dir(document.id) / "document.json"
        self.save_json(path, document.to_dict())
        return path

    def load_document(self, document_id: str) -> Document:
        return Document.from_dict(self.load_json(self.document_dir(document_id) / "document.json"))

    def save_document_profile(self, profile: DocumentProfile) -> Path:
        path = self.document_dir(profile.document_id) / "document_profile.json"
        self.save_json(path, profile.to_dict())
        return path

    def load_document_profile(self, document_id: str) -> DocumentProfile:
        return DocumentProfile.from_dict(self.load_json(self.document_dir(document_id) / "document_profile.json"))

    def list_documents(self) -> List[Document]:
        documents = []
        for path in sorted(self.processed_dir.glob("*/document.json")):
            try:
                documents.append(Document.from_dict(self.load_json(path)))
            except (KeyError, json.JSONDecodeError, TypeError, ValueError):
                continue
        return documents

    def save_chunks(self, document_id: str, chunks: Iterable[Chunk]) -> Path:
        path = self.document_dir(document_id) / "chunks.json"
        self.save_json(path, {"document_id": document_id, "chunks": [chunk.to_dict() for chunk in chunks]})
        return path

    def load_chunks(self, document_id: str) -> List[Chunk]:
        path = self.document_dir(document_id) / "chunks.json"
        payload = self.load_json(path)
        return [Chunk.from_dict(item) for item in payload.get("chunks", [])]

    def save_knowledge_graph(self, document_id: str, payload: Dict[str, Any]) -> Path:
        path = self.document_dir(document_id) / "knowledge_graph.json"
        self.save_json(path, payload)
        return path

    def load_knowledge_graph(self, document_id: str) -> Dict[str, Any]:
        return self.load_json(self.document_dir(document_id) / "knowledge_graph.json")

    def save_index(self, document_id: str, index_name: str, payload: Dict[str, Any]) -> Path:
        path = self.indexes_dir / document_id / f"{index_name}.json"
        self.save_json(path, payload)
        return path

    def load_index(self, document_id: str, index_name: str) -> Dict[str, Any]:
        return self.load_json(self.indexes_dir / document_id / f"{index_name}.json")

    def save_run(self, run_id: str, name: str, payload: Dict[str, Any]) -> Path:
        path = self.runs_dir / run_id / name
        self.save_json(path, payload)
        return path

    def load_run(self, run_id: str, name: str) -> Dict[str, Any]:
        return self.load_json(self.runs_dir / run_id / name)

    def list_runs(self) -> List[Dict[str, Any]]:
        runs = []
        for path in sorted(self.runs_dir.iterdir(), reverse=True):
            if not path.is_dir():
                continue
            files = sorted(item.name for item in path.iterdir() if item.is_file())
            runs.append({"id": path.name, "path": str(path), "files": files})
        return runs
