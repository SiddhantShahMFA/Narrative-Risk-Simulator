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
    """
    Parse uploaded file content into a list of Document objects based on the file extension.
    
    Parameters:
        filename (str): Original uploaded filename; extension determines parsing logic.
        content (bytes): File contents encoded as UTF-8.
        default_source_type (SourceType | None): Default source type required for `.txt`/`.md` inputs; ignored for `.csv` and `.json`.
        title_override (str | None): If provided, overrides the generated title for `.txt`/`.md` inputs.
    
    Returns:
        list[Document]: Parsed Document objects extracted from the uploaded content.
    
    Raises:
        ValueError: If the file extension is unsupported, or if parsing/validation of the file contents fails.
    """
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
    """
    Constructs a Document representing an uploaded plain text or Markdown file, deriving a title from the filename unless overridden.
    
    Parameters:
        filename (str): Original uploaded filename; used to generate the document id and derive a title when `title_override` is not provided.
        content (str): File contents to use as the document body.
        default_source_type (SourceType | None): Source type to assign to the Document; must be provided.
        title_override (str | None): Explicit title to use instead of deriving one from `filename`.
    
    Returns:
        Document: A validated Document with an id based on `filename`, the chosen title, `default_source_type`, the trimmed body, and a fixed summary of "Uploaded text document".
    
    Raises:
        ValueError: If `default_source_type` is None.
    """
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
    """
    Parse CSV content into a list of validated Document objects.
    
    Parameters:
        filename (str): Original uploaded filename used to generate stable document IDs.
        text (str): CSV file content as a UTF-8 decoded string. Must include a header row.
    
    Returns:
        list[Document]: Documents constructed from CSV rows that contain non-empty `title`, `source_type`, and `body`.
    
    Raises:
        ValueError: If the CSV is missing a header row or any of the required columns (`title`, `source_type`, `body`).
        ValueError: If a row fails validation; the error message includes the 1-based CSV line number of the invalid row.
    Notes:
        - Rows that are empty or that lack `title`, `source_type`, or `body` are skipped.
        - `tags` are split by commas and trimmed; empty tags are discarded.
    """
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
    """
    Parse a JSON payload into a list of validated Document objects.
    
    Accepts a JSON object representing a single document, a JSON object with a "documents" key, or a JSON list of document objects. If an item lacks an "id", one is injected based on the filename and item index before validation.
    
    Returns:
        list[Document]: List of validated Document instances.
    
    Raises:
        ValueError: If the top-level JSON is not an object or list as required, if any item is not a JSON object, or if validation of an item fails (the error message includes the item index and validation details).
    """
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
    """
    Create a stable, normalized document identifier derived from a filename and index.
    
    Parameters:
        filename (str): The original filename; only the stem (name without extension) is used.
        index (int): Zero-based index appended to the identifier.
    
    Returns:
        str: Identifier in the form "upload-{safe_name}-{index}", where `safe_name` is the filename stem converted to lowercase and with spaces and underscores replaced by dashes.
    """
    safe_name = Path(filename).stem.replace(" ", "-").replace("_", "-").lower()
    return f"upload-{safe_name}-{index}"


def _split_tags(raw: str | None) -> list[str]:
    """
    Parse a comma-separated tag string into a list of trimmed tag values.
    
    Parameters:
        raw (str | None): Comma-separated tags; may be None or an empty string.
    
    Returns:
        list[str]: A list of tags with surrounding whitespace removed. Returns an empty list if `raw` is falsy or contains no valid tags.
    """
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]
