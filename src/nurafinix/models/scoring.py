"""Scoring models and rubric for prospect prioritization."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScoringRubric(BaseModel):
    """The scoring rubric configuration."""

    # Maximum points per category
    MAX_FIT_POINTS: int = 25
    MAX_DEMAND_POINTS: int = 30
    MAX_OPPORTUNITY_POINTS: int = 25
    MAX_CONTACT_POINTS: int = 10
    MAX_EVIDENCE_POINTS: int = 10
    TOTAL_MAX: int = 100

    # Score caps based on evidence
    CAP_NO_DEMAND: int = 69  # Max score when no direct demand evidence
    CAP_NO_VERIFIED_PROBLEM: int = 39  # Max score when no verified problem/demand


class ScoreComponents(BaseModel):
    """Individual score components with evidence."""

    fit_score: float = Field(ge=0, le=25, default=0)
    fit_evidence: list[str] = Field(default_factory=list)
    fit_reasons: list[str] = Field(default_factory=list)

    demand_score: float = Field(ge=0, le=30, default=0)
    demand_evidence: list[str] = Field(default_factory=list)
    demand_reasons: list[str] = Field(default_factory=list)

    opportunity_score: float = Field(ge=0, le=25, default=0)
    opportunity_evidence: list[str] = Field(default_factory=list)
    opportunity_reasons: list[str] = Field(default_factory=list)

    contact_score: float = Field(ge=0, le=10, default=0)
    contact_evidence: list[str] = Field(default_factory=list)
    contact_reasons: list[str] = Field(default_factory=list)

    evidence_score: float = Field(ge=0, le=10, default=0)
    evidence_quality: list[str] = Field(default_factory=list)

    uncertainty: float = Field(ge=0, le=1, default=0)
    uncertainty_reasons: list[str] = Field(default_factory=list)


class ProspectScore(BaseModel):
    """Complete prospect score with all components."""

    business_id: str
    total_score: float = Field(ge=0, le=100, default=0)
    components: ScoreComponents = Field(default_factory=ScoreComponents)
    capped: bool = False
    cap_reason: str | None = None
    rubric: ScoringRubric = Field(default_factory=ScoringRubric)

    @property
    def priority_level(self) -> str:
        """Determine priority level from score."""
        if self.total_score >= 80:
            return "HIGH"
        elif self.total_score >= 60:
            return "MEDIUM"
        elif self.total_score >= 40:
            return "LOW"
        return "NONE"
