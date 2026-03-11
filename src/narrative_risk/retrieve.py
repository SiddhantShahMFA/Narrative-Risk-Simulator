"""Retrieval orchestration."""

from __future__ import annotations

from narrative_risk.index import EmbeddingIndex
from narrative_risk.models import RetrievedEvidence, SourceType


def retrieve_evidence(index: EmbeddingIndex, draft: str, limit: int = 8) -> list[RetrievedEvidence]:
    candidates = index.query(draft, limit=limit * 3)
    if not candidates:
        return []

    diversified: list[RetrievedEvidence] = []
    seen_titles: set[tuple[str, str]] = set()
    priority_types = [
        SourceType.SPONSOR_GUIDELINE,
        SourceType.POLICY,
        SourceType.CRISIS_CASE,
        SourceType.TREND,
        SourceType.STATEMENT,
    ]

    for source_type in priority_types:
        for item in candidates:
            key = (item.document_id, item.snippet)
            if item.source_type == source_type and key not in seen_titles:
                diversified.append(item)
                seen_titles.add(key)
                break

    for item in candidates:
        key = (item.document_id, item.snippet)
        if key in seen_titles:
            continue
        diversified.append(item)
        seen_titles.add(key)
        if len(diversified) >= limit:
            break

    return diversified[:limit]
