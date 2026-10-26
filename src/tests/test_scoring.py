"""Tests for scoring system."""

import pytest

from nurafinix.models.scoring import ScoreComponents, ProspectScore, ScoringRubric
from nurafinix.activities.qualification import calculate_score
from nurafinix.models.prospect import (
    CandidateBusiness,
    EvidenceRecord,
    EvidenceCategory,
    EvidenceStatus,
    VerificationMethod,
)


class TestScoringRubric:
    """Test scoring rubric configuration."""
    
    def test_rubric_defaults(self):
        """Test rubric has correct default values."""
        rubric = ScoringRubric()
        
        assert rubric.MAX_FIT_POINTS == 25
        assert rubric.MAX_DEMAND_POINTS == 30
        assert rubric.MAX_OPPORTUNITY_POINTS == 25
        assert rubric.MAX_CONTACT_POINTS == 10
        assert rubric.MAX_EVIDENCE_POINTS == 10
        assert rubric.TOTAL_MAX == 100
        assert rubric.CAP_NO_DEMAND == 69
        assert rubric.CAP_NO_VERIFIED_PROBLEM == 39


class TestScoreCaps:
    """Test score capping logic."""
    
    def test_cap_no_demand(self):
        """Test that score is capped at 69 when no direct demand evidence."""
        rubric = ScoringRubric()
        
        # Create a candidate with high scores but no demand evidence
        candidate = CandidateBusiness(
            business_id="test-1",
            name="Test Corp",
        )
        
        # Create qualification with high scores
        qualification = {
            "fit_score": 25,
            "demand_score": 0,  # No demand
            "opportunity_score": 25,
            "contact_score": 10,
            "cited_evidence": [],
            "relevant_opportunities": [],
        }
        
        # Create evidence without demand signals
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-1",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS enabled",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        # Calculate score
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            qualification=qualification,
            rubric=rubric,
        )
        
        # Score should be capped at 69
        assert score.capped is True
        assert score.cap_reason == "no_direct_demand"
        assert score.total_score <= 69
    
    def test_cap_no_verified_problem(self):
        """Test that score is capped at 39 when no verified problem."""
        rubric = ScoringRubric()
        
        candidate = CandidateBusiness(
            business_id="test-2",
            name="Test Corp 2",
        )
        
        qualification = {
            "fit_score": 25,
            "demand_score": 0,
            "opportunity_score": 0,  # No verified opportunity
            "contact_score": 10,
            "cited_evidence": [],
            "relevant_opportunities": [],
        }
        
        evidence = []  # No evidence
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            qualification=qualification,
            rubric=rubric,
        )
        
        # Score should be capped at 39
        assert score.capped is True
        assert score.cap_reason == "no_verified_problem"
        assert score.total_score <= 39
    
    def test_no_cap_with_demand_and_problem(self):
        """Test that score is not capped when both demand and problem exist."""
        rubric = ScoringRubric()
        
        candidate = CandidateBusiness(
            business_id="test-3",
            name="Test Corp 3",
        )
        
        qualification = {
            "fit_score": 25,
            "demand_score": 30,
            "opportunity_score": 25,
            "contact_score": 10,
            "cited_evidence": [],
            "relevant_opportunities": [],
        }
        
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-3",
                source_url="https://test.com",
                category=EvidenceCategory.DEMAND_SIGNAL,
                observation="Job listing for data engineer",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
            EvidenceRecord(
                evidence_id="ev-2",
                business_id="test-3",
                source_url="https://test.com",
                category=EvidenceCategory.TECH_FINGERPRINT,
                observation="React detected",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            qualification=qualification,
            rubric=rubric,
        )
        
        # Score should not be capped
        assert score.capped is False
        assert score.cap_reason is None
        # Total should be high (all max scores)
        assert score.total_score >= 80


class TestScoreCalculation:
    """Test score calculation logic."""
    
    def test_evidence_score_calculation(self):
        """Test evidence score calculation."""
        candidate = CandidateBusiness(
            business_id="test-evidence",
            name="Test Corp",
        )
        
        # Evidence with various confidence levels
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-evidence",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
            EvidenceRecord(
                evidence_id="ev-2",
                business_id="test-evidence",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=0.5,
                status=EvidenceStatus.VERIFIED,
            ),
            EvidenceRecord(
                evidence_id="ev-3",
                business_id="test-evidence",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=0.5,
                status=EvidenceStatus.UNCERTAIN,
            ),
        ]
        
        qualification = {
            "fit_score": 0,
            "demand_score": 0,
            "opportunity_score": 0,
            "contact_score": 0,
            "cited_evidence": [],
            "relevant_opportunities": [],
        }
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            qualification=qualification,
        )
        
        # Evidence score should be calculated based on quality
        assert score.components.evidence_score > 0
        assert score.components.evidence_score <= 10
    
    def test_score_with_all_components(self):
        """Test score with all components."""
        candidate = CandidateBusiness(
            business_id="test-all",
            name="Test Corp",
        )
        
        qualification = {
            "fit_score": 20,
            "demand_score": 20,
            "opportunity_score": 20,
            "contact_score": 8,
            "cited_evidence": ["ev-1", "ev-2"],
            "relevant_opportunities": ["Opportunity 1", "Opportunity 2"],
        }
        
        evidence = [
            EvidenceRecord(
                evidence_id="ev-1",
                business_id="test-all",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
            EvidenceRecord(
                evidence_id="ev-2",
                business_id="test-all",
                source_url="https://test.com",
                category=EvidenceCategory.ANALYTICS_SCRIPT,
                observation="Google Analytics",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            qualification=qualification,
        )
        
        # Check all components are present
        assert score.components.fit_score == 20
        assert score.components.demand_score == 20
        assert score.components.opportunity_score == 20
        assert score.components.contact_score == 8
        
        # Total should be sum of all components (plus evidence score)
        base_total = 20 + 20 + 20 + 8
        assert score.total_score >= base_total
        assert score.total_score <= 100


class TestProspectScorePriority:
    """Test priority level calculation from score."""
    
    def test_high_priority(self):
        """Test high priority threshold."""
        score = ProspectScore(
            business_id="test",
            total_score=85,
        )
        assert score.priority_level == "HIGH"
        
        score = ProspectScore(
            business_id="test",
            total_score=80,
        )
        assert score.priority_level == "HIGH"
    
    def test_medium_priority(self):
        """Test medium priority threshold."""
        score = ProspectScore(
            business_id="test",
            total_score=70,
        )
        assert score.priority_level == "MEDIUM"
        
        score = ProspectScore(
            business_id="test",
            total_score=60,
        )
        assert score.priority_level == "MEDIUM"
    
    def test_low_priority(self):
        """Test low priority threshold."""
        score = ProspectScore(
            business_id="test",
            total_score=50,
        )
        assert score.priority_level == "LOW"
        
        score = ProspectScore(
            business_id="test",
            total_score=40,
        )
        assert score.priority_level == "LOW"
    
    def test_no_priority(self):
        """Test no priority threshold."""
        score = ProspectScore(
            business_id="test",
            total_score=30,
        )
        assert score.priority_level == "NONE"
        
        score = ProspectScore(
            business_id="test",
            total_score=0,
        )
        assert score.priority_level == "NONE"
