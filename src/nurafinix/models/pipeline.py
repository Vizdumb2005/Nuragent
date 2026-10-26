"""Pipeline and workflow models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .prospect import CandidateBusiness, EvidenceRecord
from .scoring import ProspectScore
from .outreach import OutreachDraft


class PipelineStage(str, Enum):
    """Stages in the prospecting pipeline."""

    DISCOVERY = "discovery"
    NORMALIZATION = "normalization"
    DEDUPLICATION = "deduplication"
    EVIDENCE_COLLECTION = "evidence_collection"
    WEBSITE_AUDIT = "website_audit"
    DEMAND_ANALYSIS = "demand_analysis"
    QUALIFICATION = "qualification"
    SCORING = "scoring"
    DRAFT_GENERATION = "draft_generation"
    EVIDENCE_REVIEW = "evidence_review"
    HUMAN_APPROVAL = "human_approval"
    LEAD_TRACKING = "lead_tracking"
    EXPORT = "export"


class StageResult(BaseModel):
    """Result of a single pipeline stage."""

    stage: PipelineStage
    completed: bool = True
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float | None = None


class ProspectingInput(BaseModel):
    """Input to the prospecting workflow."""

    # CSV import path (relative or absolute)
    csv_path: str | None = None
    # CSV content as string (alternative to path)
    csv_content: str | None = None
    # Search parameters for discovery
    search_query: str | None = None
    search_limit: int = 10
    # Service categories to match
    service_categories: list[str] = Field(default_factory=list)
    # Batch processing limit
    batch_limit: int = 5
    # Mock mode (no actual API calls)
    mock_mode: bool = False


class ProspectingResult(BaseModel):
    """Complete result of a prospecting workflow execution."""

    execution_id: str
    started_at: datetime
    completed_at: datetime | None = None
    input: ProspectingInput
    candidates: list[CandidateBusiness] = Field(default_factory=list)
    evidence_map: dict[str, list[EvidenceRecord]] = Field(default_factory=dict)
    score_map: dict[str, ProspectScore] = Field(default_factory=dict)
    draft_map: dict[str, OutreachDraft] = Field(default_factory=dict)
    approval_map: dict[str, Any] = Field(default_factory=dict)
    stage_results: list[StageResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
