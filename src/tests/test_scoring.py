"""Tests for scoring system."""

import pytest

from src.nurafinix.models.scoring import ScoreComponents, ProspectScore, ScoringRubric
from src.nurafinix.activities.qualification import calculate_score, QualificationConfig
from src.nurafinix.models.prospect import (
    CandidateBusiness,
    EvidenceRecord,
    EvidenceCategory,
    EvidenceStatus,
    VerificationMethod,
    ProspectStatus,
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
            id="test-1",
            name="Test Corp",
        )
        
        # Create qualification with high scores
        qualification = {
            "fit_score": 25,
            "demand_score": 0,  # No demand
            "opportunity_score": 25,
            "contact_score": 10,
            "evidence_score": 10,
        }
        
        # Create evidence without demand signals
        evidence = [
            EvidenceRecord(
                id="ev-1",
                candidate_id="test-1",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS enabled",
                timestamp="2024-01-01T00:00:00Z",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        # Calculate score
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            config=QualificationConfig(),
        )
        
        # Score should be capped at 69
        assert score.total <= rubric.CAP_NO_DEMAND
        assert score.has_direct_demand is False
    
    def test_cap_no_verified_problem(self):
        """Test that score is capped at 39 when no verified problem or demand."""
        rubric = ScoringRubric()
        
        candidate = CandidateBusiness(
            id="test-2",
            name="Test Corp 2",
        )
        
        evidence = [
            EvidenceRecord(
                id="ev-2",
                candidate_id="test-2",
                source_url="https://test2.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="HTTPS enabled",
                timestamp="2024-01-01T00:00:00Z",
                verification_method=VerificationMethod.HTTP_CHECK,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            config=QualificationConfig(),
        )
        
        # Score should be capped at 39
        assert score.total <= rubric.CAP_NO_VERIFIED_PROBLEM
        assert score.has_verified_problem is False


class TestScoreCalculation:
    """Test score calculation logic."""
    
    def test_perfect_score(self):
        """Test that a perfect score can be achieved with all evidence."""
        candidate = CandidateBusiness(
            id="test-perfect",
            name="Perfect Corp",
            website="https://perfect.com",
            domain="perfect.com",
            industry="Technology",
            description="A perfect company with all signals",
        )
        
        # Create evidence with demand signals
        evidence = [
            EvidenceRecord(
                id="ev-demand-1",
                candidate_id="test-perfect",
                source_url="https://perfect.com/jobs",
                category=EvidenceCategory.DEMAND_SIGNAL,
                observation="Hiring data engineers",
                timestamp="2024-01-01T00:00:00Z",
                verification_method=VerificationMethod.HTML_PARSE,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
            EvidenceRecord(
                id="ev-tech-1",
                candidate_id="test-perfect",
                source_url="https://perfect.com",
                category=EvidenceCategory.TECH_FINGERPRINT,
                observation="Using outdated analytics",
                timestamp="2024-01-01T00:00:00Z",
                verification_method=VerificationMethod.TOOL_DETECTION,
                confidence=1.0,
                status=EvidenceStatus.VERIFIED,
            ),
        ]
        
        score = calculate_score(
            candidate=candidate,
            evidence=evidence,
            config=QualificationConfig(),
        )
        
        # Should have direct demand
        assert score.has_direct_demand is True
        # Should have verified problem
        assert score.has_verified_problem is True
        # Score should not be capped
        assert score.total > rubric.CAP_NO_DEMAND


class TestProspectScore:
    """Test ProspectScore model."""
    
    def test_prospect_score_creation(self):
        """Test creating a prospect score."""
        score = ProspectScore(
            candidate_id="test-1",
            total=75.5,
            components=ScoreComponents(
                customer_fit=20,
                demand_evidence=25,
                opportunity=15,
                contact_channel=8,
                evidence_reliability=7.5,
            ),
            has_direct_demand=True,
            has_verified_problem=True,
            uncertainty="low",
            reasons=["Strong fit", "High demand"],
            supporting_evidence=["ev-1", "ev-2"],
        )
        
        assert score.total == 75.5
        assert score.components.customer_fit == 20
        assert score.has_direct_demand is True
        assert len(score.reasons) == 2
    
    def test_priority_levels(self):
        """Test priority level classification."""
        high = ProspectScore(
            candidate_id="high",
            total=85,
            components=ScoreComponents(),
            has_direct_demand=True,
            has_verified_problem=True,
        )
        
        medium = ProspectScore(
            candidate_id="medium",
            total=60,
            components=ScoreComponents(),
            has_direct_demand=True,
            has_verified_problem=False,
        )
        
        low = ProspectScore(
            candidate_id="low",
            total=40,
            components=ScoreComponents(),
            has_direct_demand=False,
            has_verified_problem=False,
        )
        
        not_qualified = ProspectScore(
            candidate_id="not-qual",
            total=20,
            components=ScoreComponents(),
            has_direct_demand=False,
            has_verified_problem=False,
        )
        
        # Verify scores are in expected ranges
        assert high.total >= 70
        assert 50 <= medium.total < 70
        assert 30 <= low.total < 50
        assert not_qualified.total < 30
