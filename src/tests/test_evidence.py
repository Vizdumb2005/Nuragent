"""Tests for evidence collection activities."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from nurafinix.activities.evidence import (
    collect_website_evidence,
    audit_website,
    analyze_demand,
    _is_safe_url,
    _generate_evidence_id,
)
from nurafinix.models.prospect import (
    CandidateBusiness,
    EvidenceRecord,
    EvidenceCategory,
    EvidenceStatus,
    VerificationMethod,
)


class TestSafetyChecks:
    """Test URL safety checks."""
    
    def test_safe_urls(self):
        """Test that safe URLs are identified correctly."""
        assert _is_safe_url("https://example.com") is True
        assert _is_safe_url("http://example.com") is True
        assert _is_safe_url("https://sub.example.com/path") is True
    
    def test_unsafe_urls(self):
        """Test that unsafe URLs are blocked."""
        # Private IP addresses
        assert _is_safe_url("http://localhost") is False
        assert _is_safe_url("http://127.0.0.1") is False
        assert _is_safe_url("http://192.168.1.1") is False
        assert _is_safe_url("http://10.0.0.1") is False
        
        # Non-HTTP schemes
        assert _is_safe_url("file:///etc/passwd") is False
        assert _is_safe_url("ftp://example.com") is False
        assert _is_safe_url("javascript:alert(1)") is False
    
    def test_invalid_urls(self):
        """Test that invalid URLs are handled."""
        assert _is_safe_url("not-a-url") is False
        assert _is_safe_url("") is False


class TestEvidenceIDGeneration:
    """Test evidence ID generation."""
    
    def test_generate_evidence_id(self):
        """Test evidence ID generation."""
        id1 = _generate_evidence_id("biz-1", "https", "https://test.com")
        id2 = _generate_evidence_id("biz-1", "https", "https://test.com")
        id3 = _generate_evidence_id("biz-1", "mobile", "https://test.com")
        
        # Same inputs should produce same ID
        assert id1 == id2
        # Different category should produce different ID
        assert id1 != id3
        # IDs should be 16 characters
        assert len(id1) == 16


class TestEvidenceCollection:
    """Test evidence collection."""
    
    @pytest.mark.asyncio
    async def test_collect_website_evidence_no_website(self):
        """Test evidence collection when no website."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
            website=None,
        )
        
        evidence = await collect_website_evidence(candidate)
        
        assert evidence == []
    
    @pytest.mark.asyncio
    async def test_collect_website_evidence_unsafe_url(self):
        """Test evidence collection with unsafe URL."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
            website="http://localhost",
        )
        
        evidence = await collect_website_evidence(candidate)
        
        # Should return evidence with unavailable status
        assert len(evidence) == 1
        assert evidence[0].status == EvidenceStatus.UNAVAILABLE
        assert evidence[0].category == EvidenceCategory.WEBSITE_HTTPS


class TestWebsiteAudit:
    """Test website audit."""
    
    @pytest.mark.asyncio
    async def test_audit_website_no_website(self):
        """Test audit when no website."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
            website=None,
        )
        
        result = await audit_website(candidate)
        
        assert result["status"] == "skipped"
        assert result["reason"] == "no_website"
    
    @pytest.mark.asyncio
    async def test_audit_website_unsafe_url(self):
        """Test audit with unsafe URL."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
            website="http://localhost",
        )
        
        result = await audit_website(candidate)
        
        assert result["status"] == "blocked"
        assert result["reason"] == "safety_check_failed"


class TestDemandAnalysis:
    """Test demand analysis."""
    
    @pytest.mark.asyncio
    async def test_analyze_demand_no_evidence(self):
        """Test demand analysis with no evidence."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
        )
        
        result = await analyze_demand(candidate, [])
        
        assert result["business_id"] == "test-1"
        assert result["has_direct_demand"] is False
        assert result["has_indirect_signals"] is False
        assert result["demand_strength"] == "low"
    
    @pytest.mark.asyncio
    async def test_analyze_demand_with_demand_signal(self):
        """Test demand analysis with demand signal evidence."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
        )
        
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-1",
                source_url="https://test.com",
                category=EvidenceCategory.DEMAND_SIGNAL,
                observation="Job listing for data engineer",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        result = await analyze_demand(candidate, evidence)
        
        assert result["has_direct_demand"] is False  # DEMAND_SIGNAL is indirect
        assert result["has_indirect_signals"] is True
        assert result["demand_strength"] == "medium"
    
    @pytest.mark.asyncio
    async def test_analyze_demand_with_job_listing(self):
        """Test demand analysis with job listing evidence."""
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
        )
        
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-1",
                source_url="https://test.com",
                category=EvidenceCategory.JOB_LISTING,
                observation="Hiring data scientist",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        result = await analyze_demand(candidate, evidence)
        
        assert result["has_direct_demand"] is True
        assert result["demand_strength"] == "high"
