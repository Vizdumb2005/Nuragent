"""
Evidence collection activities for website inspection and signal detection.
"""

import httpx
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import mistralai.workflows as workflows

from ..models.prospect import (
    CandidateBusiness,
    EvidenceCategory,
    EvidenceRecord,
    EvidenceStatus,
    VerificationMethod,
)

logger = logging.getLogger(__name__)


@dataclass
class InspectionConfig:
    """Configuration for website inspection."""
    timeout_seconds: float = 10.0
    max_redirects: int = 5
    max_response_size: int = 2_000_000  # 2MB
    user_agent: str = (
        "Mozilla/5.0 (compatible; Nurafinix-Prospect-Engine/1.0; +https://nuragent.io)"
    )
    allowed_schemes: tuple[str, ...] = ("http", "https")
    blocked_domains: tuple[str, ...] = (
        "localhost",
        "127.0.0.1",
        "192.168.",
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
    )


@dataclass
class InspectionResult:
    """Result of a single website inspection."""
    candidate_id: str
    url: str
    success: bool
    status_code: int | None = None
    error: str | None = None
    html_content: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    redirect_chain: list[str] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)


def _is_safe_url(url: str, config: InspectionConfig) -> bool:
    """Check if URL is safe to inspect (SSRF protection)."""
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in config.allowed_schemes:
            logger.warning(f"Blocked URL (invalid scheme): {url}")
            return False
        
        # Check for blocked domains
        hostname = parsed.hostname or ""
        for blocked in config.blocked_domains:
            if hostname == blocked or hostname.startswith(blocked):
                logger.warning(f"Blocked URL (blocked domain): {url}")
                return False
        
        # Check for IP addresses
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
            logger.warning(f"Blocked URL (IP address): {url}")
            return False
        
        return True
    except Exception:
        return False


def _detect_https_status(
    url: str,
    response: httpx.Response,
    candidate_id: str,
) -> EvidenceRecord | None:
    """Detect HTTPS and certificate status."""
    if not url.startswith("https://"):
        return EvidenceRecord(
            id=f"{candidate_id}-https-missing",
            candidate_id=candidate_id,
            category=EvidenceCategory.SECURITY,
            observation="Website does not use HTTPS",
            source_url=url,
            timestamp=datetime.utcnow().isoformat() + "Z",
            verification_method=VerificationMethod.HTTPS_CHECK,
            confidence=1.0,
            status=EvidenceStatus.VERIFIED,
            details={"url": url},
        )
    
    # Check if HTTPS was used
    return EvidenceRecord(
        id=f"{candidate_id}-https-valid",
        candidate_id=candidate_id,
        category=EvidenceCategory.SECURITY,
        observation="Website uses HTTPS",
        source_url=url,
        timestamp=datetime.utcnow().isoformat() + "Z",
        verification_method=VerificationMethod.HTTPS_CHECK,
        confidence=1.0,
        status=EvidenceStatus.VERIFIED,
        details={"url": url, "status_code": response.status_code},
    )


def _detect_mobile_viewport(
    html: str,
    candidate_id: str,
    url: str,
) -> EvidenceRecord | None:
    """Detect mobile viewport meta tag."""
    viewport_pattern = re.compile(
        r'<meta[^>]*name=["\']viewport["\'][^>]*>',
        re.IGNORECASE,
    )
    
    if viewport_pattern.search(html):
        return EvidenceRecord(
            id=f"{candidate_id}-mobile-viewport",
            candidate_id=candidate_id,
            category=EvidenceCategory.TECHNICAL,
            observation="Mobile viewport meta tag found",
            source_url=url,
            timestamp=datetime.utcnow().isoformat() + "Z",
            verification_method=VerificationMethod.HTML_INSPECTION,
            confidence=0.95,
            status=EvidenceStatus.VERIFIED,
            details={"signal": "viewport_meta_tag"},
        )
    
    return None


def _detect_analytics(
    html: str,
    candidate_id: str,
    url: str,
) -> list[EvidenceRecord]:
    """Detect analytics scripts."""
    evidence = []
    
    # Google Analytics
    ga_patterns = [
        r'google-analytics\.com/ga\.js',
        r'google-analytics\.com/analytics\.js',
        r'googletagmanager\.com/gtm\.js',
        r'UA-\d+-\d+',
        r'G-\w+',
    ]
    
    for pattern in ga_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-analytics-ga",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.TECHNICAL,
                    observation="Google Analytics detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTML_INSPECTION,
                    confidence=0.9,
                    status=EvidenceStatus.VERIFIED,
                    details={"analytics": "google_analytics"},
                )
            )
            break
    
    return evidence


def _detect_contact_form(
    html: str,
    candidate_id: str,
    url: str,
) -> EvidenceRecord | None:
    """Detect contact form on page."""
    # Look for form elements with contact-related terms
    contact_patterns = [
        r'<form[^>]*action=["\'].*contact["\']',
        r'<form[^>]*id=["\']contact["\']',
        r'<input[^>]*type=["\']email["\']',
        r'<input[^>]*name=["\']email["\']',
    ]
    
    for pattern in contact_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return EvidenceRecord(
                id=f"{candidate_id}-contact-form",
                candidate_id=candidate_id,
                category=EvidenceCategory.CONTACT,
                observation="Contact form detected on page",
                source_url=url,
                timestamp=datetime.utcnow().isoformat() + "Z",
                verification_method=VerificationMethod.HTML_INSPECTION,
                confidence=0.8,
                status=EvidenceStatus.VERIFIED,
                details={"signal": "contact_form"},
            )
    
    return None


def _detect_broken_links(
    html: str,
    base_url: str,
    candidate_id: str,
) -> list[EvidenceRecord]:
    """Detect broken internal links (simplified check)."""
    evidence = []
    
    # Extract href attributes
    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
    links = href_pattern.findall(html)
    
    broken_count = 0
    for link in links:
        # Skip external links and anchors
        if link.startswith(("http://", "https://", "#", "mailto:", "tel:", "javascript:")):
            continue
        
        # Check if it's a relative link
        try:
            full_url = urljoin(base_url, link)
            parsed = urlparse(full_url)
            
            # Only check same-domain links
            if parsed.hostname and parsed.hostname != urlparse(base_url).hostname:
                continue
            
            # This is a simplified check - in production, you'd actually request these
            # For now, we just count potential internal links
            broken_count += 1
        except Exception:
            pass
    
    if broken_count > 0:
        evidence.append(
            EvidenceRecord(
                id=f"{candidate_id}-links-detected",
                candidate_id=candidate_id,
                category=EvidenceCategory.TECHNICAL,
                observation=f"Found {len(links)} links on page",
                source_url=base_url,
                timestamp=datetime.utcnow().isoformat() + "Z",
                verification_method=VerificationMethod.HTML_INSPECTION,
                confidence=0.9,
                status=EvidenceStatus.VERIFIED,
                details={"total_links": len(links), "internal_links": broken_count},
            )
        )
    
    return evidence


def _detect_tech_fingerprints(
    html: str,
    headers: dict[str, str],
    candidate_id: str,
    url: str,
) -> list[EvidenceRecord]:
    """Detect technology fingerprints."""
    evidence = []
    
    # Check for common frameworks in HTML
    frameworks = {
        "React": r'react\.js|ReactDOM\.render|data-reactroot',
        "Vue": r'vue\.js|data-v-',
        "Angular": r'ng-|angular\.js',
        "WordPress": r'wp-content|/wp-',
        "Shopify": r'shopify\.com|cdn\.shopify',
    }
    
    for tech_name, pattern in frameworks.items():
        if re.search(pattern, html, re.IGNORECASE):
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-tech-{tech_name.lower()}",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.TECHNICAL,
                    observation=f"{tech_name} detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTML_INSPECTION,
                    confidence=0.85,
                    status=EvidenceStatus.VERIFIED,
                    details={"technology": tech_name},
                )
            )
    
    # Check headers for server info
    server = headers.get("server", "").lower()
    if server:
        if "nginx" in server:
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-server-nginx",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.TECHNICAL,
                    observation="Nginx server detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTTP_HEADERS,
                    confidence=0.95,
                    status=EvidenceStatus.VERIFIED,
                    details={"server": "nginx"},
                )
            )
        elif "apache" in server:
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-server-apache",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.TECHNICAL,
                    observation="Apache server detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTTP_HEADERS,
                    confidence=0.95,
                    status=EvidenceStatus.VERIFIED,
                    details={"server": "apache"},
                )
            )
    
    return evidence


def _detect_demand_signals(
    html: str,
    candidate_id: str,
    url: str,
) -> list[EvidenceRecord]:
    """Detect demand signals (job listings, project requests, etc.)."""
    evidence = []
    
    # Job/career page patterns
    job_patterns = [
        r'/careers|/jobs|/work-with-us',
        r'hiring|we\'re hiring|join our team',
        r'job opening|position available',
    ]
    
    for pattern in job_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-demand-hiring",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.DEMAND,
                    observation="Hiring/job signals detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTML_INSPECTION,
                    confidence=0.7,
                    status=EvidenceStatus.VERIFIED,
                    details={"signal": "hiring"},
                )
            )
            break
    
    # Project request patterns
    project_patterns = [
        r'request a quote|get a quote',
        r'contact us for|reach out for',
        r'project inquiry|custom development',
        r'rfp|request for proposal',
    ]
    
    for pattern in project_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            evidence.append(
                EvidenceRecord(
                    id=f"{candidate_id}-demand-projects",
                    candidate_id=candidate_id,
                    category=EvidenceCategory.DEMAND,
                    observation="Project request signals detected",
                    source_url=url,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    verification_method=VerificationMethod.HTML_INSPECTION,
                    confidence=0.8,
                    status=EvidenceStatus.VERIFIED,
                    details={"signal": "project_request"},
                )
            )
            break
    
    return evidence


@workflows.activity.define(
    name="inspect_website",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=2.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=30,
)
async def inspect_website(
    candidate: CandidateBusiness,
    config: InspectionConfig | None = None,
) -> InspectionResult:
    """
    Inspect a single website and collect evidence.
    """
    if config is None:
        config = InspectionConfig()
    
    url = candidate.website
    
    # Safety check
    if not _is_safe_url(url, config):
        logger.warning(f"Skipping unsafe URL: {url}")
        return InspectionResult(
            candidate_id=candidate.id,
            url=url,
            success=False,
            error="URL blocked by safety check",
        )
    
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
            max_redirects=config.max_redirects,
            headers={"User-Agent": config.user_agent},
        ) as client:
            response = await client.get(url)
            
            # Check for oversized response
            if len(response.content) > config.max_response_size:
                logger.warning(f"Oversized response from {url}: {len(response.content)} bytes")
                return InspectionResult(
                    candidate_id=candidate.id,
                    url=url,
                    success=False,
                    error="Response too large",
                )
            
            html = response.text
            headers = dict(response.headers)
            
            # Collect all evidence
            evidence: list[EvidenceRecord] = []
            
            # HTTPS status
            https_evidence = _detect_https_status(url, response, candidate.id)
            if https_evidence:
                evidence.append(https_evidence)
            
            # Mobile viewport
            viewport_evidence = _detect_mobile_viewport(html, candidate.id, url)
            if viewport_evidence:
                evidence.append(viewport_evidence)
            
            # Analytics
            analytics_evidence = _detect_analytics(html, candidate.id, url)
            evidence.extend(analytics_evidence)
            
            # Contact form
            contact_evidence = _detect_contact_form(html, candidate.id, url)
            if contact_evidence:
                evidence.append(contact_evidence)
            
            # Broken links (simplified)
            links_evidence = _detect_broken_links(html, url, candidate.id)
            evidence.extend(links_evidence)
            
            # Technology fingerprints
            tech_evidence = _detect_tech_fingerprints(html, headers, candidate.id, url)
            evidence.extend(tech_evidence)
            
            # Demand signals
            demand_evidence = _detect_demand_signals(html, candidate.id, url)
            evidence.extend(demand_evidence)
            
            logger.info(f"Inspected {url}: {len(evidence)} evidence records collected")
            
            return InspectionResult(
                candidate_id=candidate.id,
                url=url,
                success=True,
                status_code=response.status_code,
                html_content=html[:10000] if html else None,  # Truncate for storage
                headers=headers,
                evidence=evidence,
            )
    
    except httpx.RequestError as e:
        logger.error(f"HTTP error inspecting {url}: {e}")
        return InspectionResult(
            candidate_id=candidate.id,
            url=url,
            success=False,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Error inspecting {url}: {e}")
        return InspectionResult(
            candidate_id=candidate.id,
            url=url,
            success=False,
            error=str(e),
        )


@workflows.activity.define(
    name="collect_evidence",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=2.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def collect_evidence(
    candidates: list[CandidateBusiness],
    config: InspectionConfig | None = None,
    max_concurrent: int = 5,
) -> dict[str, InspectionResult]:
    """
    Collect evidence for multiple candidates in parallel.
    """
    if config is None:
        config = InspectionConfig()
    
    logger.info(f"Collecting evidence for {len(candidates)} candidates")
    
    results: dict[str, InspectionResult] = {}
    
    # Process sequentially for now (parallel execution handled by workflow)
    for candidate in candidates:
        result = await inspect_website(candidate, config)
        results[candidate.id] = result
    
    return results


@workflows.activity.define(
    name="verify_evidence",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=1.0,
        max_delay=5.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=30,
)
async def verify_evidence(
    evidence_records: list[EvidenceRecord],
    candidate_id: str,
) -> list[EvidenceRecord]:
    """
    Verify evidence records and mark stale/uncertain ones.
    """
    logger.info(f"Verifying {len(evidence_records)} evidence records for {candidate_id}")
    
    verified = []
    for record in evidence_records:
        # Check if evidence is stale (older than 30 days)
        record_time = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
        age_days = (datetime.utcnow() - record_time).days
        
        if age_days > 30:
            record.status = EvidenceStatus.STALE
            record.confidence *= 0.5  # Reduce confidence for stale evidence
        
        verified.append(record)
    
    return verified
