"""Core data models for the simulator."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    STATEMENT = "statement"
    CRISIS_CASE = "crisis_case"
    POLICY = "policy"
    SPONSOR_GUIDELINE = "sponsor_guideline"
    TREND = "trend"


class Verdict(str, Enum):
    SAFE_TO_PUBLISH = "safe_to_publish"
    NEEDS_REVIEW = "needs_review"
    HOLD = "hold"

    @property
    def label(self) -> str:
        return {
            Verdict.SAFE_TO_PUBLISH: "Safe to publish",
            Verdict.NEEDS_REVIEW: "Needs review",
            Verdict.HOLD: "Hold",
        }[self]


class AxisScores(BaseModel):
    fan: int = Field(ge=0, le=100)
    sponsor: int = Field(ge=0, le=100)
    legal_policy: int = Field(ge=0, le=100)
    media_escalation: int = Field(ge=0, le=100)


class Document(BaseModel):
    id: str
    title: str
    source_type: SourceType
    date: dt.date | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    body: str
    risk_notes: str = ""

    @field_validator("title", "body")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        raise ValueError("tags must be a string or list")


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source_type: SourceType
    text: str
    summary: str = ""
    date: dt.date | None = None
    tags: list[str] = Field(default_factory=list)
    risk_notes: str = ""
    chunk_index: int = 0
    total_chunks: int = 1


class RetrievedEvidence(BaseModel):
    document_id: str
    title: str
    source_type: SourceType
    snippet: str
    similarity: float = Field(ge=0.0, le=1.0)
    summary: str = ""
    risk_notes: str = ""


class AnalysisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    verdict: Verdict
    axis_scores: AxisScores
    top_reasons: list[str]
    likely_narratives: list[str] = Field(default_factory=list)
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    alternative_draft: str

    @field_validator("top_reasons")
    @classmethod
    def three_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != 3:
            raise ValueError("top_reasons must contain exactly 3 items")
        return cleaned


class LLMAnalysisPayload(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    axis_scores: AxisScores
    top_reasons: list[str]
    likely_narratives: list[str] = Field(default_factory=list)
    alternative_draft: str

    @field_validator("top_reasons")
    @classmethod
    def normalize_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) < 3:
            raise ValueError("top_reasons must contain at least 3 items")
        return cleaned[:3]

    @field_validator("likely_narratives")
    @classmethod
    def normalize_narratives(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("alternative_draft")
    @classmethod
    def rewrite_is_present(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("alternative_draft must not be empty")
        return stripped


AllowedUploadSource = Literal[
    "statement",
    "crisis_case",
    "policy",
    "sponsor_guideline",
    "trend",
]


def verdict_for_score(score: int) -> Verdict:
    if score >= 70:
        return Verdict.HOLD
    if score >= 40:
        return Verdict.NEEDS_REVIEW
    return Verdict.SAFE_TO_PUBLISH


def build_analysis_result(
    payload: LLMAnalysisPayload,
    evidence: list[RetrievedEvidence],
) -> AnalysisResult:
    return AnalysisResult(
        overall_score=payload.overall_score,
        verdict=verdict_for_score(payload.overall_score),
        axis_scores=payload.axis_scores,
        top_reasons=payload.top_reasons[:3],
        likely_narratives=payload.likely_narratives,
        evidence=evidence,
        alternative_draft=payload.alternative_draft,
    )
