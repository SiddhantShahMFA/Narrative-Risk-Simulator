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
        """
        Human-readable label for the verdict.
        
        Returns:
            str: The label corresponding to the verdict (e.g., "Safe to publish", "Needs review", "Hold").
        """
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
        """
        Ensure a text value is not empty after trimming surrounding whitespace.
        
        Returns:
            The input string with leading and trailing whitespace removed.
        
        Raises:
            ValueError: If the trimmed string is empty.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str]:
        """
        Normalize a tags input into a list of non-empty, trimmed tag strings.
        
        Parameters:
            value (object): Tags provided as None, a comma-separated string, or a list of items convertible to strings.
        
        Returns:
            list[str]: A list of trimmed, non-empty tag strings.
        
        Raises:
            ValueError: If `value` is not None, a string, or a list.
        """
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
        """
        Validate and normalize a list of reason strings to exactly three trimmed, non-empty items.
        
        Parameters:
            value (list[str]): Candidate reason strings; items may include surrounding whitespace.
        
        Returns:
            list[str]: Exactly three reason strings, trimmed of surrounding whitespace.
        
        Raises:
            ValueError: If the cleaned list does not contain exactly three items.
        """
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
        """
        Normalize a list of reason strings by trimming whitespace and selecting exactly three non-empty items.
        
        Parameters:
            value (list[str]): Candidate reason strings; may contain empty or whitespace-only entries.
        
        Returns:
            list[str]: The first three non-empty, trimmed reason strings.
        
        Raises:
            ValueError: If fewer than three non-empty reason strings remain after trimming.
        """
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) < 3:
            raise ValueError("top_reasons must contain at least 3 items")
        return cleaned[:3]

    @field_validator("likely_narratives")
    @classmethod
    def normalize_narratives(cls, value: list[str]) -> list[str]:
        """
        Normalize a list of narrative strings by trimming whitespace and removing empty entries.
        
        Parameters:
            value (list[str]): List of narrative strings to clean.
        
        Returns:
            list[str]: The cleaned list containing only non-empty, trimmed narratives.
        """
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("alternative_draft")
    @classmethod
    def rewrite_is_present(cls, value: str) -> str:
        """
        Ensure the alternative draft is present and returns it trimmed.
        
        Parameters:
            value (str): The alternative draft text to validate and normalize.
        
        Returns:
            str: The trimmed alternative draft.
        
        Raises:
            ValueError: If the trimmed value is empty.
        """
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
    """
    Map a numeric risk score to the corresponding Verdict.
    
    Parameters:
        score (int): Risk score on a 0–100 scale.
    
    Returns:
        Verdict.HOLD if score is greater than or equal to 70, Verdict.NEEDS_REVIEW if score is greater than or equal to 40, Verdict.SAFE_TO_PUBLISH otherwise.
    """
    if score >= 70:
        return Verdict.HOLD
    if score >= 40:
        return Verdict.NEEDS_REVIEW
    return Verdict.SAFE_TO_PUBLISH


def build_analysis_result(
    payload: LLMAnalysisPayload,
    evidence: list[RetrievedEvidence],
) -> AnalysisResult:
    """
    Compose an AnalysisResult from an LLMAnalysisPayload and a list of retrieved evidence.
    
    Parameters:
        payload (LLMAnalysisPayload): Source of analysis fields; its overall_score determines the verdict.
        evidence (list[RetrievedEvidence]): Evidence items to attach to the resulting AnalysisResult.
    
    Returns:
        AnalysisResult: Model populated with fields from `payload`, `verdict` derived from `payload.overall_score`, and `evidence` set to the provided list.
    """
    return AnalysisResult(
        overall_score=payload.overall_score,
        verdict=verdict_for_score(payload.overall_score),
        axis_scores=payload.axis_scores,
        top_reasons=payload.top_reasons[:3],
        likely_narratives=payload.likely_narratives,
        evidence=evidence,
        alternative_draft=payload.alternative_draft,
    )
