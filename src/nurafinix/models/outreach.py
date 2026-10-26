"""Outreach and approval models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OutreachStatus(str, Enum):
    """Status of an outreach draft."""

    DRAFT = "draft"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    BOUNCED = "bounced"
    REPLIED = "replied"
    CONVERTED = "converted"


class OutreachDraft(BaseModel):
    """Personalized outreach draft for a prospect."""

    draft_id: str
    business_id: str
    subject: str | None = None
    body: str
    service_offer: str | None = None
    evidence_references: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    status: OutreachStatus = OutreachStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: str | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    notes: str | None = None
    business_name: str | None = None

    # Validation: ensure no unsupported claims
    def validate_no_unsupported_claims(self) -> list[str]:
        """Check for unsupported claims in the draft."""
        unsupported_patterns = [
            "we have worked together",
            "our previous project",
            "as you know",
            "we achieved",
            "we delivered",
            "our ROI",
            "testimonial",
            "case study",
            "guaranteed",
            "proven results",
            "trusted by",
            "used by",
        ]
        issues = []
        body_lower = self.body.lower()
        for pattern in unsupported_patterns:
            if pattern in body_lower:
                issues.append(f"Unsupported claim detected: '{pattern}'")
        return issues


class ApprovalRequest(BaseModel):
    """Request for human approval of a prospect or draft."""

    request_id: str
    business_id: str
    draft_id: str | None = None
    item_type: str = "prospect"  # or "draft"
    status: str = "pending"  # pending, approved, rejected
    requested_by: str = "system"
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    comments: str | None = None
    decision_reason: str | None = None
