"""Seed corpus loading."""

from __future__ import annotations

import json
from pathlib import Path

from narrative_risk.config import SEED_DIR
from narrative_risk.models import Document


def load_seed_documents(seed_dir: Path = SEED_DIR) -> list[Document]:
    """
    Load Document objects from all JSON files in a directory.
    
    Scans the given seed_dir for files with a .json extension, parses each file's JSON payload, and aggregates validated Document instances. If a file's JSON is an object containing a "documents" key, that value is used; otherwise the file must contain a top-level list of document items.
    
    Parameters:
    	seed_dir (Path): Directory containing seed JSON files.
    
    Returns:
    	list[Document]: A list of validated Document instances aggregated from all seed files.
    
    Raises:
    	ValueError: If a seed file's JSON payload is not a list (after handling a possible top-level "documents" key).
    """
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
