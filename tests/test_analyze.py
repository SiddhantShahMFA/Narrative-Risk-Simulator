from __future__ import annotations

import json

from narrative_risk.analyze import NarrativeRiskAnalyzer
from narrative_risk.models import RetrievedEvidence, SourceType, Verdict


def test_analyzer_returns_structured_result() -> None:
    analyzer = NarrativeRiskAnalyzer(llm=lambda _: json.dumps(_valid_payload(72)))
    result = analyzer.analyze("Launch statement", _sample_evidence())

    assert result.overall_score == 72
    assert result.verdict == Verdict.HOLD
    assert len(result.top_reasons) == 3
    assert result.evidence


def test_analyzer_repairs_malformed_json() -> None:
    calls: list[str] = []

    def fake_llm(prompt: str) -> str:
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
