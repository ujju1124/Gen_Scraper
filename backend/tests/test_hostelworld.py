"""
Unit tests for Hostelworld scraper.

These tests verify that the scraper:
1. Returns a list of results (may be empty if no selectors configured)
2. Logs scraper.started event
3. Navigates to correct Hostelworld URL
4. Inherits from BaseScraper correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.hostelworld import HostelworldScraper
from models.source import Source


@pytest.mark.asyncio
async def test_hostelworld_scraper_returns_list():
    """Test that Hostelworld scraper returns a list (may be empty if no selectors)."""
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
    
    # Assert list returned (may be empty if selectors not configured)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_hostelworld_scraper_logs_scraper_started():
    """Test that Hostelworld scraper logs scraper.started event."""
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
        
        # Assert logger.info was called with "scraper.started"
        # Find the call with event "scraper.started"
        started_calls = [call for call in mock_logger.info.call_args_list 
                        if len(call[0]) > 0 and call[0][0] == "scraper.started"]
        
        assert len(started_calls) >= 1, "scraper.started should be logged"
        
        # Check that required kwargs are present in the first started call
        call_kwargs = started_calls[0][1]
        assert "source_name" in call_kwargs
        assert call_kwargs["source_name"] == "hostelworld"
        assert "location" in call_kwargs
        assert call_kwargs["location"] == "Pokhara"
    
    # Assert results is a list (may be empty if no selectors configured)
    assert isinstance(results, list)


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
    
    # Should return a list
    assert isinstance(results, list)


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
        
        # All should return a list
        assert isinstance(results, list)


def test_hostelworld_scraper_can_be_instantiated():
    """Test that Hostelworld scraper can be instantiated without errors."""
    scraper = HostelworldScraper()
    assert scraper is not None
    assert hasattr(scraper, '_scrape')
    assert hasattr(scraper, 'source_name')


@pytest.mark.asyncio
async def test_hostelworld_scraper_navigates_to_url():
    """Test that scraper navigates to the correct Hostelworld URL."""
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
    
    # Assert page.goto was called with correct URL
    mock_page.goto.assert_called()
    call_args = mock_page.goto.call_args
    assert "hostelworld.com" in call_args[0][0]
    assert "kathmandu" in call_args[0][0].lower()
    
    # Assert results is a list
    assert isinstance(results, list)
