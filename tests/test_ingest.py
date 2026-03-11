from __future__ import annotations

import json

import pytest

from narrative_risk.ingest import parse_uploaded_documents
from narrative_risk.models import SourceType


def test_parse_txt_upload_with_metadata() -> None:
    documents = parse_uploaded_documents(
        "draft-notes.txt",
        b"Supporters will receive a detailed refund update tomorrow.",
        default_source_type=SourceType.POLICY,
        title_override="Refund Protocol",
    )

    assert len(documents) == 1
    assert documents[0].title == "Refund Protocol"
    assert documents[0].source_type == SourceType.POLICY


def test_parse_csv_upload_with_minimum_columns() -> None:
    payload = (
        "title,source_type,body\n"
        "Sponsor Rules,sponsor_guideline,Use legal review for betting sponsors.\n"
    ).encode("utf-8")

    documents = parse_uploaded_documents("rules.csv", payload)

    assert len(documents) == 1
    assert documents[0].source_type == SourceType.SPONSOR_GUIDELINE
    assert documents[0].body.startswith("Use legal review")


def test_parse_json_list_upload() -> None:
    payload = json.dumps(
        [
            {
                "title": "Trend Snapshot",
                "source_type": "trend",
                "body": "Media attention is focused on betting sponsors near youth audiences.",
            }
        ]
    ).encode("utf-8")

    documents = parse_uploaded_documents("trends.json", payload)

    assert len(documents) == 1
    assert documents[0].source_type == SourceType.TREND


def test_unsupported_upload_format_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_uploaded_documents("rules.pdf", b"not supported")


def test_missing_csv_columns_raise_clear_error() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        parse_uploaded_documents("bad.csv", b"title,body\nMissing source type,Body text\n")
