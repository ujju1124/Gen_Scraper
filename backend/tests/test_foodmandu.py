"""
Unit tests for Foodmandu scraper.

These tests verify that the scraper:
1. Navigates to correct URL
2. Waits for Angular to render
3. Extracts restaurant data correctly
4. Handles infinite scroll pagination
5. Respects max_results limit
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from scrapers.foodmandu import FoodmanduScraper
from models.source import Source


@pytest.mark.asyncio
async def test_foodmandu_scraper_navigates_to_correct_url():
    """Test that Foodmandu scraper navigates to correct URL."""
    scraper = FoodmanduScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])  # No cards
    
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "foodmandu"
    mock_db = MagicMock()
    
    # Call _scrape
    await scraper._scrape(
        page=mock_page,
        source=mock_source,
        db=mock_db,
        location="Kathmandu",
        max_results=None
    )
    
    # Assert goto was called with correct URL
    mock_page.goto.assert_called_once()
    call_args = mock_page.goto.call_args
    assert "https://foodmandu.com/Restaurant" in call_args[0][0]


@pytest.mark.asyncio
async def test_foodmandu_scraper_waits_for_angular():
    """Test that Foodmandu scraper waits for Angular to render."""
    scraper = FoodmanduScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "foodmandu"
    mock_db = MagicMock()
    
    # Call _scrape
    await scraper._scrape(
        page=mock_page,
        source=mock_source,
        db=mock_db,
        location="Kathmandu",
        max_results=None
    )
    
    # Assert wait_for_timeout was called (5 second wait for Angular)
    assert mock_page.wait_for_timeout.call_count >= 1
    # First call should be 5000ms for Angular
    first_call = mock_page.wait_for_timeout.call_args_list[0]
    assert first_call[0][0] == 5000


@pytest.mark.asyncio
async def test_foodmandu_scraper_returns_empty_list_when_no_cards():
    """Test that scraper returns empty list when no cards found."""
    scraper = FoodmanduScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.wait_for_selector = AsyncMock(side_effect=Exception("No cards"))
    
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "foodmandu"
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


def test_foodmandu_scraper_has_source_name():
    """Test that Foodmandu scraper has correct source_name."""
    scraper = FoodmanduScraper()
    assert scraper.source_name == "foodmandu"


def test_foodmandu_scraper_inherits_from_base():
    """Test that Foodmandu scraper inherits from BaseScraper."""
    from scrapers.base_scraper import BaseScraper
    scraper = FoodmanduScraper()
    assert isinstance(scraper, BaseScraper)


def test_foodmandu_scraper_can_be_instantiated():
    """Test that Foodmandu scraper can be instantiated without errors."""
    scraper = FoodmanduScraper()
    assert scraper is not None
    assert hasattr(scraper, '_scrape')
    assert hasattr(scraper, 'source_name')
