"""Tests for Pydantic models."""

import pytest
from datetime import datetime

from nurafinix.models.prospect import (
    BusinessRecord,
    CandidateBusiness,
    ContactInfo,
    ServiceCategory,
    ProspectStatus,
    EvidenceRecord,
    EvidenceCategory,
    EvidenceStatus,
    VerificationMethod,
)
from nurafinix.models.scoring import ScoreComponents, ProspectScore, ScoringRubric
from nurafinix.models.pipeline import (
    ProspectingInput,
    ProspectingResult,
    PipelineStage,
    StageResult,
)
from nurafinix.models.outreach import OutreachDraft, OutreachStatus, ApprovalRequest


class TestServiceCategory:
    """Test ServiceCategory enum."""
    
    def test_service_categories_exist(self):
        """Test that all service categories are defined."""
        assert ServiceCategory.DATA_ANALYTICS.value == "data_analytics"
        assert ServiceCategory.SQL_PYTHON_REPORTING.value == "sql_python_reporting"
        assert ServiceCategory.WEB_DEVELOPMENT.value == "web_development"
        assert ServiceCategory.SOFTWARE_FEATURES.value == "software_features"
        assert ServiceCategory.INTEGRATIONS.value == "integrations"
        assert ServiceCategory.BUSINESS_AUTOMATION.value == "business_automation"
        assert ServiceCategory.AI_ML_ENGINEERING.value == "ai_ml_engineering"
        assert ServiceCategory.DATA_ENGINEERING.value == "data_engineering"


class TestProspectStatus:
    """Test ProspectStatus enum."""
    
    def test_prospect_status_values(self):
        """Test that prospect status values are correct."""
        assert ProspectStatus.DISCOVERED.value == "discovered"
        assert ProspectStatus.NORMALIZED.value == "normalized"
        assert ProspectStatus.QUALIFIED.value == "qualified"
        assert ProspectStatus.APPROVED.value == "approved"
        assert ProspectStatus.REJECTED.value == "rejected"


class TestEvidenceCategory:
    """Test EvidenceCategory enum."""
    
    def test_evidence_categories(self):
        """Test evidence category values."""
        assert EvidenceCategory.WEBSITE_HTTPS.value == "website_https"
        assert EvidenceCategory.WEBSITE_MOBILE.value == "website_mobile"
        assert EvidenceCategory.CONTACT_FORM.value == "contact_form"
        assert EvidenceCategory.ANALYTICS_SCRIPT.value == "analytics_script"
        assert EvidenceCategory.TECH_FINGERPRINT.value == "tech_fingerprint"
        assert EvidenceCategory.DEMAND_SIGNAL.value == "demand_signal"


class TestBusinessRecord:
    """Test BusinessRecord model."""
    
    def test_business_record_creation(self):
        """Test creating a business record."""
        record = BusinessRecord(
            name="Test Corp",
            website="https://test.com",
            description="A test company",
            category="Data,Analytics",
            size="100-200",
            location="San Francisco",
            source="csv",
            raw_data={"custom_field": "value"},
        )
        
        assert record.name == "Test Corp"
        assert record.website == "https://test.com"
        assert record.description == "A test company"
        assert record.source == "csv"
        assert record.raw_data["custom_field"] == "value"
    
    def test_business_record_optional_fields(self):
        """Test business record with optional fields."""
        record = BusinessRecord(
            name="Minimal Corp",
            website=None,
            description=None,
        )
        
        assert record.name == "Minimal Corp"
        assert record.website is None
        assert record.description is None


class TestCandidateBusiness:
    """Test CandidateBusiness model."""
    
    def test_candidate_business_creation(self):
        """Test creating a candidate business."""
        candidate = CandidateBusiness(
            business_id="test-123",
            name="Test Corp",
            website="https://test.com",
            description="A test company",
            categories=[ServiceCategory.DATA_ANALYTICS],
            contact=ContactInfo(email="contact@test.com"),
            location="San Francisco",
            size="100-200",
            source="csv",
        )
        
        assert candidate.business_id == "test-123"
        assert candidate.name == "Test Corp"
        assert candidate.categories[0] == ServiceCategory.DATA_ANALYTICS
        assert candidate.contact.email == "contact@test.com"
    
    def test_candidate_defaults(self):
        """Test candidate business defaults."""
        candidate = CandidateBusiness(
            business_id="test-123",
            name="Test Corp",
            source="test",
        )
        
        assert candidate.website is None
        assert candidate.description is None
        assert candidate.categories == []
        assert candidate.contact == ContactInfo()
        assert candidate.status == ProspectStatus.DISCOVERED


class TestEvidenceRecord:
    """Test EvidenceRecord model."""
    
    def test_evidence_record_creation(self):
        """Test creating an evidence record."""
        evidence = EvidenceRecord(
            evidence_id="ev-123",
            business_id="biz-456",
            source_url="https://test.com",
            category=EvidenceCategory.WEBSITE_HTTPS,
            observation="HTTPS enabled",
            verification_method=VerificationMethod.HTTP_CHECK,
            confidence=1.0,
            status=EvidenceStatus.VERIFIED,
        )
        
        assert evidence.evidence_id == "ev-123"
        assert evidence.business_id == "biz-456"
        assert evidence.category == EvidenceCategory.WEBSITE_HTTPS
        assert evidence.confidence == 1.0
    
    def test_evidence_confidence_bounds(self):
        """Test confidence bounds."""
        # Valid confidence
        evidence = EvidenceRecord(
            evidence_id="ev-123",
            business_id="biz-456",
            source_url="https://test.com",
            category=EvidenceCategory.WEBSITE_HTTPS,
            observation="Test",
            confidence=0.5,
        )
        assert evidence.confidence == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(Exception):
            EvidenceRecord(
                evidence_id="ev-123",
                business_id="biz-456",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="Test",
                confidence=1.5,
            )
        
        # Invalid confidence (too low)
        with pytest.raises(Exception):
            EvidenceRecord(
                evidence_id="ev-123",
                business_id="biz-456",
                source_url="https://test.com",
                category=EvidenceCategory.WEBSITE_HTTPS,
                observation="Test",
                confidence=-0.1,
            )


class TestScoreComponents:
    """Test ScoreComponents model."""
    
    def test_score_components_defaults(self):
        """Test score components defaults."""
        components = ScoreComponents()
        
        assert components.fit_score == 0
        assert components.demand_score == 0
        assert components.opportunity_score == 0
        assert components.contact_score == 0
        assert components.evidence_score == 0
        assert components.uncertainty == 0
    
    def test_score_components_bounds(self):
        """Test score component bounds."""
        components = ScoreComponents(
            fit_score=25,
            demand_score=30,
            opportunity_score=25,
            contact_score=10,
            evidence_score=10,
        )
        
        assert components.fit_score == 25
        assert components.demand_score == 30
    
    def test_score_components_invalid_bounds(self):
        """Test invalid score bounds."""
        with pytest.raises(Exception):
            ScoreComponents(fit_score=26)  # Over max
        
        with pytest.raises(Exception):
            ScoreComponents(demand_score=-1)  # Under min


class TestProspectScore:
    """Test ProspectScore model."""
    
    def test_prospect_score_creation(self):
        """Test creating a prospect score."""
        score = ProspectScore(
            business_id="biz-123",
            total_score=85.5,
            components=ScoreComponents(
                fit_score=20,
                demand_score=25,
                opportunity_score=20,
                contact_score=10,
                evidence_score=10,
            ),
        )
        
        assert score.business_id == "biz-123"
        assert score.total_score == 85.5
        assert score.priority_level == "HIGH"
    
    def test_priority_levels(self):
        """Test priority level calculation."""
        high_score = ProspectScore(
            business_id="biz-1",
            total_score=85,
        )
        assert high_score.priority_level == "HIGH"
        
        medium_score = ProspectScore(
            business_id="biz-2",
            total_score=65,
        )
        assert medium_score.priority_level == "MEDIUM"
        
        low_score = ProspectScore(
            business_id="biz-3",
            total_score=45,
        )
        assert low_score.priority_level == "LOW"
        
        none_score = ProspectScore(
            business_id="biz-4",
            total_score=20,
        )
        assert none_score.priority_level == "NONE"


class TestScoringRubric:
    """Test ScoringRubric model."""
    
    def test_rubric_values(self):
        """Test rubric default values."""
        rubric = ScoringRubric()
        
        assert rubric.MAX_FIT_POINTS == 25
        assert rubric.MAX_DEMAND_POINTS == 30
        assert rubric.MAX_OPPORTUNITY_POINTS == 25
        assert rubric.MAX_CONTACT_POINTS == 10
        assert rubric.MAX_EVIDENCE_POINTS == 10
        assert rubric.TOTAL_MAX == 100
        assert rubric.CAP_NO_DEMAND == 69
        assert rubric.CAP_NO_VERIFIED_PROBLEM == 39


class TestProspectingInput:
    """Test ProspectingInput model."""
    
    def test_prospecting_input_defaults(self):
        """Test prospecting input defaults."""
        input_data = ProspectingInput()
        
        assert input_data.csv_path is None
        assert input_data.csv_content is None
        assert input_data.search_query is None
        assert input_data.search_limit == 10
        assert input_data.service_categories == []
        assert input_data.batch_limit == 5
        assert input_data.mock_mode is False
    
    def test_prospecting_input_with_values(self):
        """Test prospecting input with values."""
        input_data = ProspectingInput(
            csv_path="/path/to/file.csv",
            search_limit=20,
            batch_limit=10,
            mock_mode=True,
        )
        
        assert input_data.csv_path == "/path/to/file.csv"
        assert input_data.search_limit == 20
        assert input_data.batch_limit == 10
        assert input_data.mock_mode is True


class TestOutreachDraft:
    """Test OutreachDraft model."""
    
    def test_outreach_draft_creation(self):
        """Test creating an outreach draft."""
        draft = OutreachDraft(
            draft_id="draft-123",
            business_id="biz-456",
            subject="Potential Collaboration",
            body="Hello, we noticed...",
            service_offer="Data analytics",
            evidence_references=["ev-1", "ev-2"],
            source_urls=["https://test.com"],
        )
        
        assert draft.draft_id == "draft-123"
        assert draft.business_id == "biz-456"
        assert draft.subject == "Potential Collaboration"
        assert draft.status == OutreachStatus.DRAFT
    
    def test_validate_no_unsupported_claims(self):
        """Test validation of unsupported claims."""
        # Draft with unsupported claim
        draft = OutreachDraft(
            draft_id="draft-123",
            business_id="biz-456",
            body="We have worked together before and achieved great results.",
        )
        
        issues = draft.validate_no_unsupported_claims()
        assert len(issues) > 0
        assert any("worked together" in issue for issue in issues)
        
        # Valid draft
        valid_draft = OutreachDraft(
            draft_id="draft-123",
            business_id="biz-456",
            body="Hello, we noticed your website and thought we could help.",
        )
        
        issues = valid_draft.validate_no_unsupported_claims()
        assert len(issues) == 0


class TestStageResult:
    """Test StageResult model."""
    
    def test_stage_result_creation(self):
        """Test creating a stage result."""
        result = StageResult(
            stage=PipelineStage.DISCOVERY,
            completed=True,
            data={"count": 10},
        )
        
        assert result.stage == PipelineStage.DISCOVERY
        assert result.completed is True
        assert result.data["count"] == 10
    
    def test_stage_result_failure(self):
        """Test stage result with failure."""
        result = StageResult(
            stage=PipelineStage.EVIDENCE_COLLECTION,
            completed=False,
            error="Timeout error",
        )
        
        assert result.completed is False
        assert result.error == "Timeout error"


class TestPipelineStage:
    """Test PipelineStage enum."""
    
    def test_pipeline_stages(self):
        """Test pipeline stage values."""
        assert PipelineStage.DISCOVERY.value == "discovery"
        assert PipelineStage.NORMALIZATION.value == "normalization"
        assert PipelineStage.EVIDENCE_COLLECTION.value == "evidence_collection"
        assert PipelineStage.WEBSITE_AUDIT.value == "website_audit"
        assert PipelineStage.QUALIFICATION.value == "qualification"
        assert PipelineStage.SCORING.value == "scoring"
        assert PipelineStage.DRAFT_GENERATION.value == "draft_generation"
        assert PipelineStage.EVIDENCE_REVIEW.value == "evidence_review"
        assert PipelineStage.HUMAN_APPROVAL.value == "human_approval"
        assert PipelineStage.LEAD_TRACKING.value == "lead_tracking"
        assert PipelineStage.EXPORT.value == "export"
