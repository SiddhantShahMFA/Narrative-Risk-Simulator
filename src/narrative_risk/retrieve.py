"""Retrieval orchestration."""

from __future__ import annotations

from narrative_risk.index import EmbeddingIndex
from narrative_risk.models import RetrievedEvidence, SourceType


def retrieve_evidence(index: EmbeddingIndex, draft: str, limit: int = 8) -> list[RetrievedEvidence]:
    """
    Selects a diverse set of evidence items from an embedding index that are relevant to the given draft.
    
    Queries the provided index for candidate evidence and returns up to `limit` items chosen to maximize source-type priority and uniqueness. Items are deduplicated by (document_id, snippet) and prioritized in the order: SPONSOR_GUIDELINE, POLICY, CRISIS_CASE, TREND, STATEMENT; remaining unique candidates are included until the limit is reached.
    
    Parameters:
        index (EmbeddingIndex): The embedding index to query for evidence.
        draft (str): The draft text used as the retrieval query.
        limit (int): Maximum number of evidence items to return.
    
    Returns:
        list[RetrievedEvidence]: Up to `limit` prioritized and deduplicated evidence items.
    """
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
