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
        """
        Create a NarrativeRiskAnalyzer configured with an LLM model and callable.
        
        Parameters:
            model (str | None): Optional OpenAI model name to use; when omitted, the default model returned by `get_openai_model()` is selected.
            llm (LLMCallable | None): Optional callable that accepts a prompt string and returns the LLM's raw string response; when omitted, the instance uses its internal OpenAI-backed completion method.
        """
        self.model = model or get_openai_model()
        self._llm = llm or self._openai_complete

    def analyze(self, draft: str, evidence: list[RetrievedEvidence]) -> AnalysisResult:
        """
        Run a risk analysis of a draft using retrieved evidence and return a structured AnalysisResult.
        
        Builds a prompt from the provided draft and evidence, calls the configured LLM to obtain a JSON payload, and attempts to parse that payload into the expected analysis shape. If parsing fails, issues a repair prompt and retries parsing; if that still fails, generates a deterministic fallback payload. The final AnalysisResult is constructed from the chosen payload and up to the first six evidence items.
        
        Parameters:
            draft (str): The communication draft to analyze.
            evidence (list[RetrievedEvidence]): Retrieved evidence items to inform the analysis.
        
        Returns:
            AnalysisResult: A structured analysis including overall and axis scores, top reasons, likely narratives, and a safer alternative draft; evidence attached will be limited to the first six items.
        """
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
        """
        Parse LLM output and return a validated LLMAnalysisPayload.
        
        Attempts to decode `raw` as JSON, unwraps a top-level "analysis" object if present, and validates the resulting data against the LLMAnalysisPayload model.
        
        Parameters:
        	raw (str): JSON text produced by the LLM; may be the payload object itself or an object containing an "analysis" field.
        
        Returns:
        	LLMAnalysisPayload | None: A validated LLMAnalysisPayload on success, `None` if JSON decoding or validation fails.
        """
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
        """
        Send the given prompt to the analyzer's configured OpenAI model and return the model's textual output.
        
        Parameters:
            prompt (str): The complete prompt to send to the LLM.
        
        Returns:
            str: The raw text output produced by the model.
        """
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
        """
        Constructs the LLM prompt used to analyze a sports communications draft given retrieved evidence.
        
        Parameters:
            draft (str): The draft text to analyze.
            evidence (list[RetrievedEvidence]): Retrieved evidence items; each will be formatted with title, type, similarity, summary, risk notes, and snippet.
        
        Returns:
            str: A single prompt string that embeds the draft and a formatted evidence block (or "No evidence retrieved."), and instructs the LLM to return JSON with the exact shape:
            {
              "overall_score": 0,
              "axis_scores": {"fan": 0, "sponsor": 0, "legal_policy": 0, "media_escalation": 0},
              "top_reasons": ["", "", ""],
              "likely_narratives": ["", ""],
              "alternative_draft": ""
            }
            The prompt also enforces scoring rules (0–100), exactly three short top reasons, evidence-based reasoning when possible, and a safer rewrite of the draft; it requests JSON-only output.
        """
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
        """
        Constructs a repair prompt that instructs the LLM to convert malformed analysis output into a specific JSON shape.
        
        Parameters:
            raw (str): The malformed LLM output to be included in the repair prompt.
        
        Returns:
            prompt (str): A plain-text prompt that requests the LLM to return only valid JSON matching the exact schema for `overall_score`, `axis_scores`, `top_reasons`, `likely_narratives`, and `alternative_draft`, and includes the provided malformed output for correction.
        """
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
        """
        Constructs a heuristic LLMAnalysisPayload to use when the LLM-produced output cannot be parsed.
        
        The payload's overall score is computed from keyword triggers found in the draft and boosted by the presence of specific evidence source types; it is clamped to the range 0–100. Axis scores are derived from the overall score with small positive offsets. The returned payload also includes a set of default top reasons, likely narratives, and a safer alternative draft rewrite.
         
        Returns:
            LLMAnalysisPayload: Payload with `overall_score` (0–100), `axis_scores` (AxisScores derived from the overall score), `top_reasons` (list of explanatory strings), `likely_narratives` (list of strings), and `alternative_draft` (a suggested rewrite).
        """
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
