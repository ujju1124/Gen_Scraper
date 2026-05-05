"""
Unit tests for Hostelworld scraper stub.

These tests verify that the scraper stub:
1. Returns empty list (awaiting selectors)
2. Logs HUMAN CHECKPOINT warning
3. Inherits from BaseScraper correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.hostelworld import HostelworldScraper
from models.source import Source


@pytest.mark.asyncio
async def test_hostelworld_scraper_returns_empty_list():
    """Test that Hostelworld scraper stub returns empty list."""
    scraper = HostelworldScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "hostelworld"
    mock_db = MagicMock()
    
    # Call _scrape
    results = await scraper._scrape(
        page=mock_page,
        source=mock_source,
        db=mock_db,
        location="Kathmandu",
        max_results=None
    )
    
    # Assert empty list returned
    assert results == []
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_hostelworld_scraper_logs_human_checkpoint():
    """Test that Hostelworld scraper logs HUMAN CHECKPOINT warning."""
    scraper = HostelworldScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "hostelworld"
    mock_db = MagicMock()
    
    # Mock the logger to verify it's called
    with patch('scrapers.hostelworld.logger') as mock_logger:
        results = await scraper._scrape(
            page=mock_page,
            source=mock_source,
            db=mock_db,
            location="Pokhara",
            max_results=50
        )
        
        # Assert logger.warning was called with "scraper.human_checkpoint"
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # First argument should be the event name
        assert call_args[0][0] == "scraper.human_checkpoint"
        
        # Check that required kwargs are present
        assert "source_name" in call_args[1]
        assert call_args[1]["source_name"] == "hostelworld"
        assert "message" in call_args[1]
        assert "Selectors must be configured" in call_args[1]["message"]
    
    # Assert empty results
    assert results == []


def test_hostelworld_scraper_has_source_name():
    """Test that Hostelworld scraper has correct source_name."""
    scraper = HostelworldScraper()
    assert scraper.source_name == "hostelworld"


def test_hostelworld_scraper_inherits_from_base():
    """Test that Hostelworld scraper inherits from BaseScraper."""
    from scrapers.base_scraper import BaseScraper
    scraper = HostelworldScraper()
    assert isinstance(scraper, BaseScraper)


@pytest.mark.asyncio
async def test_hostelworld_scraper_accepts_max_results_parameter():
    """Test that Hostelworld scraper accepts max_results parameter."""
    scraper = HostelworldScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "hostelworld"
    mock_db = MagicMock()
    
    # Call with max_results
    results = await scraper._scrape(
        page=mock_page,
        source=mock_source,
        db=mock_db,
        location="Kathmandu",
        max_results=100
    )
    
    # Should still return empty list (stub)
    assert results == []


@pytest.mark.asyncio
async def test_hostelworld_scraper_accepts_different_locations():
    """Test that Hostelworld scraper accepts different location parameters."""
    scraper = HostelworldScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "hostelworld"
    mock_db = MagicMock()
    
    # Test with different locations
    locations = ["Kathmandu", "Pokhara", "Chitwan", "Lumbini"]
    
    for location in locations:
        results = await scraper._scrape(
            page=mock_page,
            source=mock_source,
            db=mock_db,
            location=location,
            max_results=None
        )
        
        # All should return empty list (stub)
        assert results == []


def test_hostelworld_scraper_can_be_instantiated():
    """Test that Hostelworld scraper can be instantiated without errors."""
    scraper = HostelworldScraper()
    assert scraper is not None
    assert hasattr(scraper, '_scrape')
    assert hasattr(scraper, 'source_name')


@pytest.mark.asyncio
async def test_hostelworld_scraper_does_not_call_page_methods():
    """Test that stub does not attempt to navigate or interact with page."""
    scraper = HostelworldScraper()
    
    # Mock page with tracking
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "hostelworld"
    mock_db = MagicMock()
    
    # Call _scrape
    results = await scraper._scrape(
        page=mock_page,
        source=mock_source,
        db=mock_db,
        location="Kathmandu",
        max_results=None
    )
    
    # Assert page methods were NOT called (stub should not navigate)
    mock_page.goto.assert_not_called()
    mock_page.query_selector.assert_not_called()
    mock_page.query_selector_all.assert_not_called()
    
    # Assert empty results
    assert results == []
