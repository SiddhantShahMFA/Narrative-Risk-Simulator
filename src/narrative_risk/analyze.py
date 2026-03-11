"""LLM-backed risk analysis."""

from __future__ import annotations

import json
from collections.abc import Callable

from openai import OpenAI
from pydantic import ValidationError

from narrative_risk.config import get_openai_model
from narrative_risk.models import (
    AnalysisResult,
    AxisScores,
    LLMAnalysisPayload,
    RetrievedEvidence,
    build_analysis_result,
)


LLMCallable = Callable[[str], str]


class NarrativeRiskAnalyzer:
    def __init__(
        self,
        *,
        model: str | None = None,
        llm: LLMCallable | None = None,
    ) -> None:
        self.model = model or get_openai_model()
        self._llm = llm or self._openai_complete

    def analyze(self, draft: str, evidence: list[RetrievedEvidence]) -> AnalysisResult:
        prompt = self._build_prompt(draft, evidence)
        raw = self._llm(prompt)
        payload = self._parse_payload(raw)
        if payload is None:
            repaired = self._llm(self._build_repair_prompt(raw))
            payload = self._parse_payload(repaired)
        if payload is None:
            payload = self._fallback_payload(draft, evidence)
        return build_analysis_result(payload, evidence[:6])

    def _parse_payload(self, raw: str) -> LLMAnalysisPayload | None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if isinstance(data, dict) and "analysis" in data and isinstance(data["analysis"], dict):
            data = data["analysis"]

        try:
            return LLMAnalysisPayload.model_validate(data)
        except ValidationError:
            return None

    def _openai_complete(self, prompt: str) -> str:
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a narrative risk analyst for sports communications teams. "
                                "Return valid JSON only."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
        )
        return response.output_text

    def _build_prompt(self, draft: str, evidence: list[RetrievedEvidence]) -> str:
        evidence_block = "\n\n".join(
            [
                (
                    f"Source: {item.title}\n"
                    f"Type: {item.source_type.value}\n"
                    f"Similarity: {item.similarity:.3f}\n"
                    f"Summary: {item.summary or 'N/A'}\n"
                    f"Risk notes: {item.risk_notes or 'N/A'}\n"
                    f"Snippet: {item.snippet}"
                )
                for item in evidence
            ]
        )
        return f"""
Analyze the sports communications draft below using the supplied evidence.

Draft:
{draft}

Retrieved evidence:
{evidence_block or "No evidence retrieved."}

Return JSON with this exact shape:
{{
  "overall_score": 0,
  "axis_scores": {{
    "fan": 0,
    "sponsor": 0,
    "legal_policy": 0,
    "media_escalation": 0
  }},
  "top_reasons": ["", "", ""],
  "likely_narratives": ["", ""],
  "alternative_draft": ""
}}

Rules:
- Score from 0 to 100.
- Provide exactly 3 short top reasons.
- Base the reasoning on the evidence when possible.
- Rewrite the draft into safer wording without losing the key announcement.
- Return JSON only.
""".strip()

    def _build_repair_prompt(self, raw: str) -> str:
        return f"""
Repair the following malformed analysis into valid JSON only.
Return this exact shape:
{{
  "overall_score": 0,
  "axis_scores": {{
    "fan": 0,
    "sponsor": 0,
    "legal_policy": 0,
    "media_escalation": 0
  }},
  "top_reasons": ["", "", ""],
  "likely_narratives": ["", ""],
  "alternative_draft": ""
}}

Malformed output:
{raw}
""".strip()

    def _fallback_payload(
        self,
        draft: str,
        evidence: list[RetrievedEvidence],
    ) -> LLMAnalysisPayload:
        lowered = draft.lower()
        triggers = {
            "boycott": 16,
            "betting": 18,
            "crypto": 15,
            "exclusive": 8,
            "apolog": 12,
            "investigation": 18,
            "lawsuit": 18,
            "alcohol": 12,
            "token": 10,
        }
        base_score = 18 + sum(weight for token, weight in triggers.items() if token in lowered)
        if any(item.source_type.value == "sponsor_guideline" for item in evidence):
            base_score += 8
        if any(item.source_type.value == "crisis_case" for item in evidence):
            base_score += 10
        if any(item.source_type.value == "trend" for item in evidence):
            base_score += 6
        overall = max(0, min(100, base_score))
        axis_scores = AxisScores(
            fan=min(100, overall + 4),
            sponsor=min(100, overall + 8),
            legal_policy=min(100, overall + 6),
            media_escalation=min(100, overall + 2),
        )
        reasons = [
            "The draft overlaps with themes that often trigger fast fan backlash.",
            "Sponsor and policy context suggests the framing could create avoidable conflict.",
            "Journalists could amplify the timing or tone before the organization sets context.",
        ]
        narratives = [
            "Hypocrisy and poor timing",
            "Commercial priorities over stakeholder trust",
        ]
        rewrite = (
            "We are announcing this decision with a clear commitment to stakeholder safety, "
            "policy compliance, and ongoing review. We recognize the sensitivity around the "
            "timing and have built additional safeguards, oversight, and feedback channels "
            "into the rollout."
        )
        return LLMAnalysisPayload(
            overall_score=overall,
            axis_scores=axis_scores,
            top_reasons=reasons,
            likely_narratives=narratives,
            alternative_draft=rewrite,
        )
