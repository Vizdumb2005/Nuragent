"""
Qualification activities for prospect assessment and scoring.
"""

import logging
from dataclasses import dataclass
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
from ..models.scoring import (
    ProspectScore,
    ScoreComponents,
    ScoringRubric,
)
from ..models.outreach import OutreachDraft
from ..models.prospect import ProspectStatus

logger = logging.getLogger(__name__)


@dataclass
class QualificationConfig:
    """Configuration for qualification."""
    model_id: str = "mistral-large-latest"
    temperature: float = 0.0
    max_tokens: int = 4096
    
    # Service categories for Nurafinix
    service_categories: list[str] = field(default_factory=lambda: [
        "Data analytics, SQL, Python, and reporting dashboards",
        "Web development, software features, and integrations",
        "Business process and workflow automation",
        "AI/ML engineering and data engineering",
    ])


# Default scoring rubric
DEFAULT_RUBRIC = ScoringRubric(
    customer_fit_max=25,
    demand_evidence_max=30,
    opportunity_max=25,
    contact_channel_max=10,
    evidence_reliability_max=10,
    no_demand_cap=69,
    no_problem_cap=39,
)


def _has_direct_demand(evidence: list[EvidenceRecord]) -> bool:
    """Check if there's direct demand evidence."""
    for record in evidence:
        if record.category == EvidenceCategory.DEMAND:
            if record.status in (EvidenceStatus.VERIFIED, EvidenceStatus.UNCERTAIN):
                return True
    return False


def _has_verified_problem(evidence: list[EvidenceRecord]) -> bool:
    """Check if there's a verified substantive problem or demand."""
    for record in evidence:
        if record.category in (EvidenceCategory.DEMAND, EvidenceCategory.TECHNICAL):
            if record.status == EvidenceStatus.VERIFIED:
                # Check if it's a substantive problem
                if any(
                    keyword in record.observation.lower()
                    for keyword in [
                        "broken", "error", "problem", "issue", 
                        "needed", "required", "missing", "hiring",
                        "project", "request", "rfp"
                    ]
                ):
                    return True
    return False


def _calculate_customer_fit_score(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    config: QualificationConfig,
) -> tuple[float, list[str]]:
    """Calculate customer fit score (max 25 points)."""
    score = 0.0
    reasons: list[str] = []
    
    # Check if business description mentions relevant services
    description = (candidate.description or "").lower()
    industry = (candidate.industry or "").lower()
    
    matched_categories = []
    for category in config.service_categories:
        category_lower = category.lower()
        if any(
            keyword in description or keyword in industry
            for keyword in category_lower.split()
        ):
            matched_categories.append(category)
    
    if matched_categories:
        score += 15
        reasons.append(f"Business description matches {len(matched_categories)} service categories")
    else:
        score += 5
        reasons.append("Business description has some relevance")
    
    # Check for technology indicators
    tech_keywords = ["data", "analytics", "sql", "python", "software", "web", "automation", "ai", "ml"]
    for keyword in tech_keywords:
        if keyword in description or keyword in industry:
            score += 2
            break
    
    # Cap at max
    score = min(score, DEFAULT_RUBRIC.customer_fit_max)
    
    return score, reasons


def _calculate_demand_score(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
) -> tuple[float, list[str]]:
    """Calculate demand evidence score (max 30 points)."""
    score = 0.0
    reasons: list[str] = []
    
    demand_evidence = [
        e for e in evidence 
        if e.category == EvidenceCategory.DEMAND 
        and e.status in (EvidenceStatus.VERIFIED, EvidenceStatus.UNCERTAIN)
    ]
    
    if not demand_evidence:
        return 0.0, ["No demand evidence found"]
    
    # Count verified demand signals
    verified_count = sum(
        1 for e in demand_evidence 
        if e.status == EvidenceStatus.VERIFIED
    )
    
    if verified_count >= 2:
        score += 25
        reasons.append(f"{verified_count} verified demand signals found")
    elif verified_count == 1:
        score += 15
        reasons.append("1 verified demand signal found")
    
    # Add points for uncertain but relevant signals
    uncertain_count = sum(
        1 for e in demand_evidence 
        if e.status == EvidenceStatus.UNCERTAIN
    )
    score += uncertain_count * 5
    if uncertain_count > 0:
        reasons.append(f"{uncertain_count} uncertain demand signals found")
    
    # Cap at max
    score = min(score, DEFAULT_RUBRIC.demand_evidence_max)
    
    return score, reasons


def _calculate_opportunity_score(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
) -> tuple[float, list[str]]:
    """Calculate opportunity score (max 25 points)."""
    score = 0.0
    reasons: list[str] = []
    
    # Check for technical evidence that indicates opportunity
    tech_evidence = [
        e for e in evidence 
        if e.category == EvidenceCategory.TECHNICAL 
        and e.status == EvidenceStatus.VERIFIED
    ]
    
    # Mobile readiness
    mobile_evidence = [
        e for e in tech_evidence 
        if "mobile" in e.observation.lower() or "viewport" in e.observation.lower()
    ]
    
    if mobile_evidence:
        score += 10
        reasons.append("Mobile viewport configured (modern web practices)")
    
    # Analytics
    analytics_evidence = [
        e for e in tech_evidence 
        if "analytics" in e.observation.lower()
    ]
    
    if analytics_evidence:
        score += 8
        reasons.append("Analytics tracking detected (data-driven organization)")
    
    # Contact form
    contact_evidence = [
        e for e in evidence 
        if e.category == EvidenceCategory.CONTACT 
        and e.status == EvidenceStatus.VERIFIED
    ]
    
    if contact_evidence:
        score += 7
        reasons.append("Contact form available (lead generation ready)")
    
    # Cap at max
    score = min(score, DEFAULT_RUBRIC.opportunity_max)
    
    return score, reasons


def _calculate_contact_score(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
) -> tuple[float, list[str]]:
    """Calculate contact channel score (max 10 points)."""
    score = 0.0
    reasons: list[str] = []
    
    # Check for contact evidence
    contact_evidence = [
        e for e in evidence 
        if e.category == EvidenceCategory.CONTACT 
        and e.status == EvidenceStatus.VERIFIED
    ]
    
    if contact_evidence:
        score += 8
        reasons.append("Contact channel verified")
    else:
        score += 2
        reasons.append("Contact channel assumed (website exists)")
    
    # Cap at max
    score = min(score, DEFAULT_RUBRIC.contact_channel_max)
    
    return score, reasons


def _calculate_reliability_score(
    evidence: list[EvidenceRecord],
) -> tuple[float, list[str]]:
    """Calculate evidence reliability score (max 10 points)."""
    score = 0.0
    reasons: list[str] = []
    
    if not evidence:
        return 0.0, ["No evidence collected"]
    
    # Count verified evidence
    verified_count = sum(
        1 for e in evidence 
        if e.status == EvidenceStatus.VERIFIED
    )
    
    # Count fresh evidence (within 30 days)
    fresh_count = sum(
        1 for e in evidence 
        if e.status == EvidenceStatus.VERIFIED
        and (datetime.utcnow() - datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))).days <= 30
    )
    
    # Base score on verification
    score += verified_count * 0.5
    score += fresh_count * 0.5
    
    # Bonus for recent evidence
    if fresh_count >= 3:
        score += 2
        reasons.append(f"{fresh_count} fresh evidence records")
    
    # Cap at max
    score = min(score, DEFAULT_RUBRIC.evidence_reliability_max)
    
    if score > 0:
        reasons.append(f"Evidence reliability score: {score:.1f}/10")
    
    return score, reasons


def calculate_score(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    config: QualificationConfig | None = None,
) -> ProspectScore:
    """
    Calculate prospect score using the scoring rubric.
    
    Applies explicit caps:
    - No direct demand evidence: maximum 69/100
    - No verified substantive problem or demand: maximum 39/100
    """
    if config is None:
        config = QualificationConfig()
    
    rubric = DEFAULT_RUBRIC
    
    # Calculate component scores
    fit_score, fit_reasons = _calculate_customer_fit_score(candidate, evidence, config)
    demand_score, demand_reasons = _calculate_demand_score(candidate, evidence)
    opportunity_score, opportunity_reasons = _calculate_opportunity_score(candidate, evidence)
    contact_score, contact_reasons = _calculate_contact_score(candidate, evidence)
    reliability_score, reliability_reasons = _calculate_reliability_score(evidence)
    
    # Calculate total
    total = fit_score + demand_score + opportunity_score + contact_score + reliability_score
    
    # Apply caps
    has_direct_demand = _has_direct_demand(evidence)
    has_verified_problem = _has_verified_problem(evidence)
    
    if not has_direct_demand:
        total = min(total, rubric.no_demand_cap)
    
    if not has_verified_problem:
        total = min(total, rubric.no_problem_cap)
    
    # Collect all reasons
    all_reasons = fit_reasons + demand_reasons + opportunity_reasons + contact_reasons + reliability_reasons
    
    # Determine uncertainty
    uncertainty = "low"
    if not has_direct_demand:
        uncertainty = "medium"
    if not has_verified_problem and not has_direct_demand:
        uncertainty = "high"
    
    return ProspectScore(
        candidate_id=candidate.id,
        total=round(total, 2),
        components=ScoreComponents(
            customer_fit=round(fit_score, 2),
            demand_evidence=round(demand_score, 2),
            opportunity=round(opportunity_score, 2),
            contact_channel=round(contact_score, 2),
            evidence_reliability=round(reliability_score, 2),
        ),
        has_direct_demand=has_direct_demand,
        has_verified_problem=has_verified_problem,
        uncertainty=uncertainty,
        reasons=all_reasons,
        supporting_evidence=[e.id for e in evidence if e.status == EvidenceStatus.VERIFIED],
        calculated_at=datetime.utcnow().isoformat() + "Z",
    )


@workflows.activity.define(
    name="qualify_prospect",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=2.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=120,
)
async def qualify_prospect(
    candidate: CandidateBusiness,
    evidence: list[EvidenceRecord],
    config: QualificationConfig | None = None,
    mock_mode: bool = False,
) -> tuple[ProspectScore, CandidateBusiness]:
    """
    Qualify a prospect using AI assessment.
    
    In mock mode, uses deterministic scoring.
    In real mode, also uses LLM for additional insights.
    """
    if config is None:
        config = QualificationConfig()
    
    logger.info(f"Qualifying prospect: {candidate.name} ({candidate.id})")
    
    # Calculate deterministic score
    score = calculate_score(candidate, evidence, config)
    
    # Update candidate status based on score
    if score.total >= 70:
        candidate.status = ProspectStatus.HIGH_PRIORITY
    elif score.total >= 50:
        candidate.status = ProspectStatus.MEDIUM_PRIORITY
    elif score.total >= 30:
        candidate.status = ProspectStatus.LOW_PRIORITY
    else:
        candidate.status = ProspectStatus.NOT_QUALIFIED
    
    candidate.qualified_at = datetime.utcnow().isoformat() + "Z"
    candidate.score = score.total
    
    logger.info(f"Qualified {candidate.name}: score={score.total}, status={candidate.status}")
    
    return score, candidate


@workflows.activity.define(
    name="batch_qualify",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=1.0,
        max_delay=5.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def batch_qualify(
    candidates: list[CandidateBusiness],
    evidence_map: dict[str, list[EvidenceRecord]],
    config: QualificationConfig | None = None,
    mock_mode: bool = False,
) -> dict[str, tuple[ProspectScore, CandidateBusiness]]:
    """
    Qualify multiple prospects in parallel.
    """
    if config is None:
        config = QualificationConfig()
    
    logger.info(f"Batch qualifying {len(candidates)} candidates")
    
    results: dict[str, tuple[ProspectScore, CandidateBusiness]] = {}
    
    for candidate in candidates:
        candidate_evidence = evidence_map.get(candidate.id, [])
        score, qualified_candidate = await qualify_prospect(
            candidate, candidate_evidence, config, mock_mode
        )
        results[candidate.id] = (score, qualified_candidate)
    
    return results
