from __future__ import annotations

import json

from narrative_risk.analyze import NarrativeRiskAnalyzer
from narrative_risk.models import RetrievedEvidence, SourceType, Verdict


def test_analyzer_returns_structured_result() -> None:
    """
    Verifies that NarrativeRiskAnalyzer correctly parses a well-formed LLM JSON payload into a structured analysis result.
    
    Asserts that the analyzer produces an overall score of 72, a verdict of Verdict.HOLD, three top reasons, and includes evidence when the LLM returns a valid JSON payload.
    """
    analyzer = NarrativeRiskAnalyzer(llm=lambda _: json.dumps(_valid_payload(72)))
    result = analyzer.analyze("Launch statement", _sample_evidence())

    assert result.overall_score == 72
    assert result.verdict == Verdict.HOLD
    assert len(result.top_reasons) == 3
    assert result.evidence


def test_analyzer_repairs_malformed_json() -> None:
    calls: list[str] = []

    def fake_llm(prompt: str) -> str:
        """
        Simulate an LLM: record the given prompt and return malformed JSON on the first invocation, then a valid JSON payload (overall_score 44) on subsequent invocations.
        
        Parameters:
        	prompt (str): The input prompt sent to the simulated LLM.
        
        Returns:
        	str: A malformed JSON string on the first call ("{not valid json"), or a JSON-encoded payload produced by _valid_payload(44) on later calls.
        
        Side effects:
        	Appends the provided prompt to the external `calls` list.
        """
        calls.append(prompt)
        if len(calls) == 1:
            return "{not valid json"
        return json.dumps(_valid_payload(44))

    analyzer = NarrativeRiskAnalyzer(llm=fake_llm)
    result = analyzer.analyze("Sponsor statement", _sample_evidence())

    assert len(calls) == 2
    assert result.overall_score == 44
    assert result.verdict == Verdict.NEEDS_REVIEW


def test_analyzer_falls_back_when_llm_stays_invalid() -> None:
    analyzer = NarrativeRiskAnalyzer(llm=lambda _: "still not json")
    result = analyzer.analyze(
        "We are pleased to announce a crypto betting token partnership.",
        _sample_evidence(),
    )

    assert result.overall_score >= 18
    assert len(result.top_reasons) == 3
    assert result.alternative_draft


def _sample_evidence() -> list[RetrievedEvidence]:
    """
    Create a deterministic sample list of RetrievedEvidence representing a sponsor guideline policy.
    
    Returns:
        list[RetrievedEvidence]: A single-item list containing a RetrievedEvidence with:
            - document_id "policy-1"
            - title "Sponsor Rules"
            - source_type SourceType.SPONSOR_GUIDELINE
            - a snippet about betting sponsors and age-gating
            - similarity 0.91
            - a brief summary about extra approvals
            - risk_notes indicating escalation if youth audiences are referenced
    """
    return [
        RetrievedEvidence(
            document_id="policy-1",
            title="Sponsor Rules",
            source_type=SourceType.SPONSOR_GUIDELINE,
            snippet="Betting sponsors require legal review and age-gating language.",
            similarity=0.91,
            summary="Sensitive sponsor categories need extra approvals.",
            risk_notes="Escalate if youth audiences are referenced.",
        )
    ]


def _valid_payload(score: int) -> dict[str, object]:
    """
    Constructs a deterministic analysis payload for tests.
    
    Parameters:
        score (int): Numeric overall risk score (e.g., 0–100) to populate the payload.
    
    Returns:
        dict[str, object]: A payload dictionary containing:
            - "overall_score" (int): the provided score.
            - "axis_scores" (dict[str, int]): per-axis scores for "fan", "sponsor", "legal_policy", and "media_escalation", all set to the provided score.
            - "top_reasons" (list[str]): three reason strings explaining the score.
            - "likely_narratives" (list[str]): candidate narrative strings.
            - "alternative_draft" (str): an alternative draft text.
    """
    return {
        "overall_score": score,
        "axis_scores": {
            "fan": score,
            "sponsor": score,
            "legal_policy": score,
            "media_escalation": score,
        },
        "top_reasons": [
            "The tone is overly celebratory for a sensitive sponsor category.",
            "The statement could conflict with sponsor and age-gating guidelines.",
            "The wording invites media framing around risk and timing.",
        ],
        "likely_narratives": ["Commercial priorities over supporter trust"],
        "alternative_draft": "We are announcing the partnership with additional safeguards and review steps in place.",
    }
