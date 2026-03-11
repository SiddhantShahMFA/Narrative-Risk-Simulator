from __future__ import annotations

from pathlib import Path

from narrative_risk.index import EmbeddingIndex
from narrative_risk.models import Document, SourceType
from narrative_risk.retrieve import retrieve_evidence


def test_sponsor_prompt_surfaces_guideline(tmp_path: Path) -> None:
    """
    Verify that a sponsor-related prompt surfaces sponsor guideline evidence from the embedding index.
    
    Creates a small set of documents including a sponsor guideline, indexes them, queries the index with a sponsor-related prompt, and asserts that evidence is returned, that at least one returned item has SourceType.SPONSOR_GUIDELINE, and that the first returned item is a sponsor guideline.
    """
    documents = [
        Document(
            id="sponsor-guideline",
            title="Sensitive Sponsor Rules",
            source_type=SourceType.SPONSOR_GUIDELINE,
            body="Betting sponsors require legal review and safer wording.",
        ),
        Document(
            id="trend-1",
            title="Media Trend",
            source_type=SourceType.TREND,
            body="Headlines are critical of betting promotions aimed near youth fans.",
        ),
        Document(
            id="statement-1",
            title="Routine Matchday Update",
            source_type=SourceType.STATEMENT,
            body="Gates open at 5pm and extra transit services will run after the match.",
        ),
    ]
    index = EmbeddingIndex(index_path=tmp_path / "index.json", embedder=_keyword_embedder)
    index.sync_documents(documents)

    evidence = retrieve_evidence(
        index,
        "We are thrilled to launch a new betting partner for supporters this weekend.",
    )

    assert evidence
    assert any(item.source_type == SourceType.SPONSOR_GUIDELINE for item in evidence)
    assert evidence[0].source_type == SourceType.SPONSOR_GUIDELINE


def test_apology_prompt_surfaces_crisis_case(tmp_path: Path) -> None:
    documents = [
        Document(
            id="case-1",
            title="Corporate Apology Backlash",
            source_type=SourceType.CRISIS_CASE,
            body="An apology that centered the brand instead of harmed athletes intensified criticism.",
        ),
        Document(
            id="policy-1",
            title="Review Checklist",
            source_type=SourceType.POLICY,
            body="Sensitive matters should acknowledge harm, actions, and ongoing review.",
        ),
    ]
    index = EmbeddingIndex(index_path=tmp_path / "index.json", embedder=_keyword_embedder)
    index.sync_documents(documents)

    evidence = retrieve_evidence(
        index,
        "We apologize if anyone was offended and regret the distraction caused to our organization.",
    )

    assert any(item.source_type == SourceType.CRISIS_CASE for item in evidence)


def _keyword_embedder(texts: list[str]) -> list[list[float]]:
    """
    Produce keyword-count embedding vectors for each input text.
    
    Parameters:
        texts (list[str]): Input strings to embed; counts are case-insensitive.
    
    Returns:
        list[list[float]]: A list of vectors where each vector contains the counts (as floats) of the keywords ["betting", "sponsor", "apolog", "harm", "legal", "media", "fans"] in the corresponding input text, in that order.
    """
    keywords = ["betting", "sponsor", "apolog", "harm", "legal", "media", "fans"]
    vectors: list[list[float]] = []
    for text in texts:
        lowered = text.lower()
        vectors.append([float(lowered.count(keyword)) for keyword in keywords])
    return vectors
