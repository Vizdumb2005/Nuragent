"""Tests for workflow activities."""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile
import os

from nurafinix.activities.discovery import (
    discover_from_csv,
    normalize_business,
    deduplicate_candidates,
    _generate_business_id,
    _parse_service_categories,
)
from nurafinix.models.prospect import BusinessRecord, CandidateBusiness, ServiceCategory


class TestCSVImport:
    """Test CSV import functionality."""
    
    @pytest.mark.asyncio
    async def test_discover_from_csv_path(self):
        """Test importing from CSV file path."""
        csv_content = """name,website,description,category,size,location
Test Corp,https://test.com,"A test company","Data,Analytics",100-200,San Francisco
Another Corp,https://another.com,"Another test","Web",50-100,New York
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            records = await discover_from_csv(csv_path=temp_path)
            
            assert len(records) == 2
            assert records[0].name == "Test Corp"
            assert str(records[0].website) == "https://test.com"
            assert records[1].name == "Another Corp"
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_discover_from_csv_content(self):
        """Test importing from CSV content string."""
        csv_content = """name,website,description
CSV Corp,https://csv.com,"From string"
"""
        
        records = await discover_from_csv(csv_content=csv_content)
        
        assert len(records) == 1
        assert records[0].name == "CSV Corp"
        assert records[0].source == "csv"


class TestNormalization:
    """Test business normalization."""
    
    @pytest.mark.asyncio
    async def test_normalize_business_basic(self):
        """Test basic business normalization."""
        record = BusinessRecord(
            name="  Test Corp  ",
            website="https://test.com",
            description="  A test company  ",
            category="Data,Analytics",
            size="100-200",
            location="San Francisco",
        )
        
        candidate = await normalize_business(record)
        
        assert candidate.name == "Test Corp"
        assert candidate.description == "A test company"
        assert str(candidate.website) == "https://test.com"
        assert candidate.location == "San Francisco"
        assert candidate.size == "100-200"
        assert candidate.status.value == "normalized"
    
    @pytest.mark.asyncio
    async def test_normalize_business_website_http(self):
        """Test website normalization without scheme."""
        record = BusinessRecord(
            name="Test Corp",
            website="test.com",
        )
        
        candidate = await normalize_business(record)
        
        assert str(candidate.website) == "https://test.com"
    
    @pytest.mark.asyncio
    async def test_normalize_service_categories(self):
        """Test service category parsing."""
        record = BusinessRecord(
            name="Test Corp",
            website="https://test.com",
            category="Data,Analytics,Web Development",
        )
        
        candidate = await normalize_business(record)
        
        assert ServiceCategory.DATA_ANALYTICS in candidate.categories
        assert ServiceCategory.SQL_PYTHON_REPORTING in candidate.categories
        assert ServiceCategory.WEB_DEVELOPMENT in candidate.categories


class TestDeduplication:
    """Test candidate deduplication."""
    
    @pytest.mark.asyncio
    async def test_deduplicate_candidates(self):
        """Test deduplication by business_id."""
        candidates = [
            CandidateBusiness(
                business_id="biz-1",
                name="Corp 1",
            ),
            CandidateBusiness(
                business_id="biz-2",
                name="Corp 2",
            ),
            CandidateBusiness(
                business_id="biz-1",  # Duplicate
                name="Corp 1 Duplicate",
            ),
            CandidateBusiness(
                business_id="biz-3",
                name="Corp 3",
            ),
        ]
        
        unique = await deduplicate_candidates(candidates)
        
        assert len(unique) == 3
        assert unique[0].business_id == "biz-1"
        assert unique[1].business_id == "biz-2"
        assert unique[2].business_id == "biz-3"
        # First occurrence should be kept
        assert unique[0].name == "Corp 1"


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_generate_business_id(self):
        """Test business ID generation."""
        id1 = _generate_business_id("Test Corp", "https://test.com")
        id2 = _generate_business_id("Test Corp", "https://test.com")
        id3 = _generate_business_id("Test Corp", "https://different.com")
        id4 = _generate_business_id("Different Corp", "https://test.com")
        
        # Same inputs should produce same ID
        assert id1 == id2
        # Different website should produce different ID
        assert id1 != id3
        # Different name should produce different ID
        assert id1 != id4
        # IDs should be 16 characters
        assert len(id1) == 16
    
    def test_parse_service_categories(self):
        """Test service category parsing."""
        categories = _parse_service_categories("Data,Analytics,AI")
        
        assert ServiceCategory.DATA_ANALYTICS in categories
        assert ServiceCategory.SQL_PYTHON_REPORTING in categories
        assert ServiceCategory.AI_ML_ENGINEERING in categories
        
        # Test empty
        empty = _parse_service_categories(None)
        assert empty == []
        
        # Test case insensitivity
        categories2 = _parse_service_categories("data,python,web development")
        assert ServiceCategory.DATA_ANALYTICS in categories2
        assert ServiceCategory.SQL_PYTHON_REPORTING in categories2
        assert ServiceCategory.WEB_DEVELOPMENT in categories2
    
    def test_parse_service_categories_no_duplicates(self):
        """Test that duplicate categories are removed."""
        categories = _parse_service_categories("Data,data,Analytics,analytics")
        
        # Should only have unique categories
        assert len(categories) == 2
        assert ServiceCategory.DATA_ANALYTICS in categories
        assert ServiceCategory.SQL_PYTHON_REPORTING in categories
