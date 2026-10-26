"""
Outreach activities for draft generation and evidence review.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import mistralai.workflows as workflows

from ..models.prospect import (
    CandidateBusiness,
    EvidenceCategory,
    EvidenceRecord,
    EvidenceStatus,
    ProspectStatus,
)
from ..models.outreach import (
    ApprovalRequest,
    OutreachDraft,
    OutreachStatus,
)
from ..models.scoring import ProspectScore

logger = logging.getLogger(__name__)


@dataclass
class OutreachConfig:
    """Configuration for outreach generation."""
    model_id: str = "mistral-large-latest"
    temperature: float = 0.3
    max_tokens: int = 2048
    
    # Company info
    company_name: str = "Nurafinix Labs"
    company_description: str = (
        "Nurafinix Labs helps businesses with data analytics, SQL, Python, "
        "reporting dashboards, web development, software features, integrations, "
        "business process automation, and AI/ML engineering."
    )
    
    # Forbidden patterns in outreach
    forbidden_patterns: list[str] = field(default_factory=lambda: [
        r'\$\d+',  # Dollar amounts
        r'\d+%',  # Percentage claims
        r'ROI|return on investment',
        r'guarantee|guaranteed',
        r'testimonial|testimony|review',
        r'client|customer|customer of ours',
        r'we worked with|we helped',
        r'proven|proven track record',
        r'industry leader|leading provider',
        r'trusted by|used by',
        r'\d+ years of experience',
        r'award|award-winning',
    ])


# Forbidden phrases for validation
FORBIDDEN_PHRASES = [
    "we have worked with",
    "we helped",
    "our client",
    "our customer",
    "testimonial",
    "review",
    "guarantee",
    "guaranteed",
    "proven",
    "industry leader",
    "trusted by",
    "used by",
    "award",
    "award-winning",
    "ROI",
    "return on investment",
    "years of experience",
]


def _generate_draft_id(candidate_id: str, service_category: str) -> str:
    """Generate a unique draft ID."""
    import hashlib
    timestamp = datetime.utcnow().isoformat()
    unique_str = f"{candidate_id}-{service_category}-{timestamp}"
    return f"draft-{hashlib.md5(unique_str.encode()).hexdigest()[:8]}"


def _validate_outreach_draft(draft: OutreachDraft) -> list[str]:
    """Validate an outreach draft for forbidden patterns."""
    errors = []
    
    content = draft.content.lower()
    
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in content:
            errors.append(f"Forbidden phrase: '{phrase}'")
    
    # Check for dollar amounts
    if re.search(r'\$\d+', draft.content):
        errors.append("Forbidden: Dollar amounts")
    
    # Check for percentage claims
    if re.search(r'\d+%', draft.content):
        errors.append("Forbidden: Percentage claims")
    
    return errors


def _extract_evidence_citations(
    evidence: list[EvidenceRecord],
    max_citations: int = 3,
) -> list[str]:
    """Extract evidence citations for the draft."""
    # Sort by confidence and recency
    sorted_evidence = sorted(
        evidence,
        key=lambda e: (e.confidence, e.timestamp),
        reverse=True,
    )
    
    citations = []
    for record in sorted_evidence[:max_citations]:
        if record.status == EvidenceStatus.VERIFIED:
            citation = f"[{record.observation}]({record.source_url})"
            citations.append(citation)
    
    return citations


def _get_service_category_for_candidate(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
) -> str:
    """Determine the most relevant service category for a candidate."""
    # Check evidence for clues
    for record in evidence:
        observation = record.observation.lower()
        
        if any(kw in observation for kw in ["data", "analytics", "sql", "python", "dashboard"]):
            return "Data analytics, SQL, Python, and reporting dashboards"
        elif any(kw in observation for kw in ["web", "website", "development", "feature", "integration"]):
            return "Web development, software features, and integrations"
        elif any(kw in observation for kw in ["automation", "workflow", "process"]):
            return "Business process and workflow automation"
        elif any(kw in observation for kw in ["ai", "ml", "machine learning", "data engineering"]):
            return "AI/ML engineering and data engineering"
    
    # Default to first category
    return "Data analytics, SQL, Python, and reporting dashboards"


def _generate_deterministic_draft(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    score: ProspectScore,
    config: OutreachConfig,
) -> OutreachDraft:
    """Generate a deterministic outreach draft (for mock mode)."""
    service_category = _get_service_category_for_candidate(candidate, evidence)
    
    # Extract relevant evidence
    relevant_evidence = [
        e for e in evidence 
        if e.status == EvidenceStatus.VERIFIED 
        and e.category in (EvidenceCategory.DEMAND, EvidenceCategory.TECHNICAL)
    ]
    
    # Build the draft
    evidence_summary = ""
    if relevant_evidence:
        evidence_items = [
            f"- {e.observation} (source: {e.source_url})"
            for e in relevant_evidence[:3]
        ]
        evidence_summary = "\n".join(evidence_items)
        evidence_summary = f"\n\nI noticed the following on your site:\n{evidence_summary}\n"
    
    subject = f"Quick question about {candidate.name}"
    
    content = f"""Hi there,

I came across {candidate.name} and was impressed by what you're building at {candidate.website}.

{evidence_summary}
I work with {config.company_name}, where we specialize in {service_category.lower()}.

Would you be open to a quick chat about how we might be able to help?

Best regards,
{config.company_name}
{config.company_description}"""
    
    draft_id = _generate_draft_id(candidate.id, service_category)
    
    return OutreachDraft(
        id=draft_id,
        candidate_id=candidate.id,
        service_category=service_category,
        subject=subject,
        content=content,
        status=OutreachStatus.DRAFT,
        evidence_used=[e.id for e in relevant_evidence],
        created_at=datetime.utcnow().isoformat() + "Z",
        updated_at=datetime.utcnow().isoformat() + "Z",
        version=1,
    )


def _personalize_draft(
    draft: OutreachDraft,
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    config: OutreachConfig,
) -> OutreachDraft:
    """Personalize a draft based on candidate and evidence."""
    # Replace placeholders
    personalized = draft.content
    
    # Add business name mentions
    if candidate.name and f"{candidate.name}" not in personalized:
        # Replace first occurrence of generic greeting
        personalized = personalized.replace(
            "Hi there,",
            f"Hi {candidate.name} team,"
        )
    
    # Add website mention if not present
    if candidate.website and f"{candidate.website}" not in personalized:
        personalized = personalized.replace(
            f"at {candidate.website}",
            f"at {candidate.website}"
        )
    
    # Update draft
    draft.content = personalized
    draft.updated_at = datetime.utcnow().isoformat() + "Z"
    draft.version += 1
    
    return draft


@workflows.activity.define(
    name="generate_outreach_draft",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=2.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=120,
)
async def generate_outreach_draft(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    score: ProspectScore,
    config: OutreachConfig | None = None,
    mock_mode: bool = False,
) -> OutreachDraft:
    """
    Generate an outreach draft for a qualified prospect.
    
    In mock mode, generates deterministic draft.
    In real mode, would use LLM for more personalized content.
    """
    if config is None:
        config = OutreachConfig()
    
    logger.info(f"Generating outreach draft for: {candidate.name} ({candidate.id})")
    
    # Generate deterministic draft (mock mode always uses this)
    draft = _generate_deterministic_draft(candidate, evidence, score, config)
    
    # Personalize it
    draft = _personalize_draft(draft, candidate, evidence, config)
    
    # Validate
    errors = _validate_outreach_draft(draft)
    if errors:
        logger.warning(f"Draft validation errors for {candidate.id}: {errors}")
        draft.validation_errors = errors
        draft.status = OutreachStatus.NEEDS_REVISION
    else:
        draft.status = OutreachStatus.READY_FOR_REVIEW
    
    logger.info(f"Generated draft {draft.id} for {candidate.name}")
    
    return draft


@workflows.activity.define(
    name="review_evidence",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=1.0,
        max_delay=5.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def review_evidence(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    score: ProspectScore,
    draft: OutreachDraft | None = None,
) -> ApprovalRequest:
    """
    Prepare an approval request with evidence review.
    """
    logger.info(f"Preparing approval request for: {candidate.name} ({candidate.id})")
    
    # Extract key evidence
    key_evidence = [
        e for e in evidence 
        if e.status == EvidenceStatus.VERIFIED
    ][:5]
    
    # Build summary
    evidence_summary = "\n".join(
        f"- [{e.observation}]({e.source_url}) (confidence: {e.confidence:.2f})"
        for e in key_evidence
    )
    
    request = ApprovalRequest(
        id=f"approval-{candidate.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        candidate_website=candidate.website,
        score=score.total,
        status=candidate.status,
        evidence_summary=evidence_summary,
        draft_id=draft.id if draft else None,
        draft_preview=draft.subject if draft else None,
        requested_at=datetime.utcnow().isoformat() + "Z",
        requested_by="system",
        notes=f"Score: {score.total}/100. {', '.join(score.reasons[:3])}",
    )
    
    logger.info(f"Prepared approval request {request.id} for {candidate.name}")
    
    return request


@workflows.activity.define(
    name="batch_outreach",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=1.0,
        max_delay=5.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def batch_outreach(
    candidates: list[CandidateBusiness],
    evidence_map: dict[str, list[EvidenceRecord]],
    score_map: dict[str, ProspectScore],
    config: OutreachConfig | None = None,
    mock_mode: bool = False,
) -> dict[str, OutreachDraft]:
    """
    Generate outreach drafts for multiple candidates.
    """
    if config is None:
        config = OutreachConfig()
    
    logger.info(f"Batch generating outreach for {len(candidates)} candidates")
    
    drafts: dict[str, OutreachDraft] = {}
    
    for candidate in candidates:
        candidate_evidence = evidence_map.get(candidate.id, [])
        candidate_score = score_map.get(candidate.id)
        
        if candidate_score and candidate_evidence:
            draft = await generate_outreach_draft(
                candidate, candidate_evidence, candidate_score, config, mock_mode
            )
            drafts[candidate.id] = draft
    
    return drafts
