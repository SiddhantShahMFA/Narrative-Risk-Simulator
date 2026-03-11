"""Input document parsing for uploaded source material."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from narrative_risk.models import Document, SourceType


SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
CSV_REQUIRED_COLUMNS = {"title", "source_type", "body"}


def parse_uploaded_documents(
    filename: str,
    content: bytes,
    *,
    default_source_type: SourceType | None = None,
    title_override: str | None = None,
) -> list[Document]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {suffix or filename}")

    if suffix in {".txt", ".md"}:
        return [
            _build_text_document(
                filename=filename,
                content=content.decode("utf-8"),
                default_source_type=default_source_type,
                title_override=title_override,
            )
        ]
    if suffix == ".csv":
        return _parse_csv(filename, content.decode("utf-8"))
    return _parse_json(filename, content.decode("utf-8"))


def _build_text_document(
    *,
    filename: str,
    content: str,
    default_source_type: SourceType | None,
    title_override: str | None,
) -> Document:
    if default_source_type is None:
        raise ValueError("A source type is required for TXT and MD uploads")

    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    title = (title_override or stem or filename).strip()
    return Document(
        id=_document_id(filename, 0),
        title=title,
        source_type=default_source_type,
        body=content.strip(),
        summary="Uploaded text document",
    )


def _parse_csv(filename: str, text: str) -> list[Document]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file is missing a header row")
    columns = {name.strip() for name in reader.fieldnames if name}
    missing = CSV_REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"CSV file is missing required columns: {', '.join(sorted(missing))}")

    documents: list[Document] = []
    for index, row in enumerate(reader):
        if not row:
            continue
        body = (row.get("body") or "").strip()
        title = (row.get("title") or "").strip()
        source_type = (row.get("source_type") or "").strip()
        if not body or not title or not source_type:
            continue
        try:
            documents.append(
                Document(
                    id=_document_id(filename, index),
                    title=title,
                    source_type=SourceType(source_type),
                    date=(row.get("date") or "").strip() or None,
                    tags=_split_tags(row.get("tags")),
                    summary=(row.get("summary") or "").strip(),
                    body=body,
                    risk_notes=(row.get("risk_notes") or "").strip(),
                )
            )
        except (ValueError, ValidationError) as exc:
            raise ValueError(f"Invalid CSV row {index + 2}: {exc}") from exc
    return documents


def _parse_json(filename: str, text: str) -> list[Document]:
    payload = json.loads(text)
    if isinstance(payload, dict):
        if "documents" in payload:
            payload = payload["documents"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("JSON upload must be a document object or a list of documents")

    documents: list[Document] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"JSON document {index + 1} must be an object")
        if "id" not in item:
            item = {"id": _document_id(filename, index), **item}
        try:
            documents.append(Document.model_validate(item))
        except ValidationError as exc:
            raise ValueError(f"Invalid JSON document {index + 1}: {exc}") from exc
    return documents


def _document_id(filename: str, index: int) -> str:
    safe_name = Path(filename).stem.replace(" ", "-").replace("_", "-").lower()
    return f"upload-{safe_name}-{index}"


def _split_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]
