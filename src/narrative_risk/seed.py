"""Seed corpus loading."""

from __future__ import annotations

import json
from pathlib import Path

from narrative_risk.config import SEED_DIR
from narrative_risk.models import Document


def load_seed_documents(seed_dir: Path = SEED_DIR) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(seed_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "documents" in payload:
            payload = payload["documents"]
        if not isinstance(payload, list):
            raise ValueError(f"Seed file {path} must contain a list of documents")
        for item in payload:
            documents.append(Document.model_validate(item))
    return documents
