"""Prospect and business models for lead generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ServiceCategory(str, Enum):
    """Service categories offered by Nurafinix Labs."""

    DATA_ANALYTICS = "data_analytics"
    SQL_PYTHON_REPORTING = "sql_python_reporting"
    WEB_DEVELOPMENT = "web_development"
    SOFTWARE_FEATURES = "software_features"
    INTEGRATIONS = "integrations"
    BUSINESS_AUTOMATION = "business_automation"
    AI_ML_ENGINEERING = "ai_ml_engineering"
    DATA_ENGINEERING = "data_engineering"


class ProspectStatus(str, Enum):
    """Current status of a prospect in the pipeline."""

    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    ENRICHED = "enriched"
    INSPECTED = "inspected"
    QUALIFIED = "qualified"
    SCORING = "scoring"
    DRAFT_READY = "draft_ready"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"
    CONTACTED = "contacted"


class EvidenceCategory(str, Enum):
    """Categories of evidence collected during prospecting."""

    WEBSITE_HTTPS = "website_https"
    WEBSITE_MOBILE = "website_mobile"
    WEBSITE_LINKS = "website_links"
    CONTACT_FORM = "contact_form"
    ANALYTICS_SCRIPT = "analytics_script"
    TECH_FINGERPRINT = "tech_fingerprint"
    DEMAND_SIGNAL = "demand_signal"
    JOB_LISTING = "job_listing"
    PROJECT_REQUEST = "project_request"


class EvidenceStatus(str, Enum):
    """Status of an evidence observation."""

    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    CONTRADICTORY = "contradictory"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class VerificationMethod(str, Enum):
    """Methods used to verify evidence."""

    HTTP_CHECK = "http_check"
    HTML_PARSE = "html_parse"
    API_CALL = "api_call"
    MANUAL_REVIEW = "manual_review"
    TOOL_DETECTION = "tool_detection"


class ContactInfo(BaseModel):
    """Contact information for a business."""

    email: str | None = None
    phone: str | None = None
    contact_form_url: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    twitter: HttpUrl | None = None


class BusinessRecord(BaseModel):
    """Raw business record from CSV import or discovery."""

    name: str
    website: str | None = None
    description: str | None = None
    category: str | None = None
    size: str | None = None
    location: str | None = None
    source: str = "csv"
    source_url: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CandidateBusiness(BaseModel):
    """Normalized and deduplicated business candidate."""

    id: str
    name: str
    website: str | None = None
    domain: str | None = None
    description: str | None = None
    industry: str | None = None
    location: str | None = None
    size: str | None = None
    source: str = "unknown"
    imported_at: str | None = None
    normalized_at: str | None = None
    qualified_at: str | None = None
    status: ProspectStatus = ProspectStatus.DISCOVERED
    score: float | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRecord(BaseModel):
    """A single evidence observation for a business."""

    id: str
    candidate_id: str
    source_url: str
    category: EvidenceCategory
    observation: str
    timestamp: str
    verification_method: VerificationMethod = VerificationMethod.HTTP_CHECK
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    status: EvidenceStatus = EvidenceStatus.VERIFIED
    details: dict[str, Any] = Field(default_factory=dict)
