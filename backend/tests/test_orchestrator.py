"""
Orchestrator Integration Tests for Web Scraping Portal Phase 2

Tests for ScraperOrchestrator:
- Domain grouping
- Sequential execution within same domain
- Parallel execution across different domains
- Failure tracking
- Partial success handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from scrapers.orchestrator import ScraperOrchestrator
from models.scrape_job import ScrapeJob
from models.source import Source


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_job():
    """Mock scrape job."""
    import uuid
    job = Mock(spec=ScrapeJob)
    job.id = uuid.uuid4()  # Use valid UUID instead of string
    job.location = "Kathmandu"
    job.category_id = 1
    job.source_ids = None
    return job


@pytest.fixture
def mock_sources():
    """Mock sources with different domains."""
    source1 = Mock(spec=Source)
    source1.id = 1
    source1.name = "booking_com"
    source1.base_url = "https://www.booking.com"
    source1.category_id = 1
    source1.is_active = True
    
    source2 = Mock(spec=Source)
    source2.id = 2
    source2.name = "agoda"
    source2.base_url = "https://www.agoda.com"
    source2.category_id = 1
    source2.is_active = True
    
    source3 = Mock(spec=Source)
    source3.id = 3
    source3.name = "booking_com_2"
    source3.base_url = "https://www.booking.com/hotels"
    source3.category_id = 1
    source3.is_active = True
    
    return [source1, source2, source3]


class TestDomainGrouping:
    """Test domain grouping functionality."""
    
    def test_group_by_domain_basic(self, mock_sources):
        """Test basic domain grouping."""
        orchestrator = ScraperOrchestrator()
        groups = orchestrator._group_by_domain(mock_sources)
        
        # Should have 2 domains: booking.com and agoda.com
        assert len(groups) == 2
        assert "booking.com" in groups
        assert "agoda.com" in groups
        
        # booking.com should have 2 sources
        assert len(groups["booking.com"]) == 2
        assert groups["booking.com"][0].id in [1, 3]
        assert groups["booking.com"][1].id in [1, 3]
        
        # agoda.com should have 1 source
        assert len(groups["agoda.com"]) == 1
        assert groups["agoda.com"][0].id == 2
    
    def test_group_by_domain_removes_www(self):
        """Test that www. prefix is removed from domains."""
        source = Mock(spec=Source)
        source.id = 1
        source.name = "test"
        source.base_url = "https://www.example.com"
        
        orchestrator = ScraperOrchestrator()
        groups = orchestrator._group_by_domain([source])
        
        assert "example.com" in groups
        assert "www.example.com" not in groups
    
    def test_group_by_domain_handles_invalid_url(self):
        """Test domain grouping with invalid URL."""
        source = Mock(spec=Source)
        source.id = 1
        source.name = "test_source"
        source.base_url = "invalid-url"
        
        orchestrator = ScraperOrchestrator()
        groups = orchestrator._group_by_domain([source])
        
        # Should fallback to source name
        assert len(groups) == 1
        assert source in list(groups.values())[0]


class TestSequentialExecution:
    """Test sequential execution within same domain."""
    
    @pytest.mark.asyncio
    async def test_sequential_execution_with_delay(self, mock_db, mock_job):
        """Test that same-domain scrapers run sequentially with delay."""
        # Create two sources with same domain
        source1 = Mock(spec=Source)
        source1.id = 1
        source1.name = "booking_com"
        source1.base_url = "https://www.booking.com"
        
        source2 = Mock(spec=Source)
        source2.id = 2
        source2.name = "booking_com_2"
        source2.base_url = "https://www.booking.com/hotels"
        
        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.run = AsyncMock(return_value=[{"name": "Hotel 1"}])
        
        orchestrator = ScraperOrchestrator()
        
        with patch('scrapers.orchestrator.get_scraper', return_value=mock_scraper):
            start_time = asyncio.get_event_loop().time()
            results, failures = await orchestrator._run_domain_group(
                mock_db, mock_job, "booking.com", [source1, source2]
            )
            end_time = asyncio.get_event_loop().time()
        
        # Should have results from both sources
        assert len(results) == 2
        assert len(failures) == 0
        
        # Should have taken at least 2 seconds (delay between requests)
        elapsed = end_time - start_time
        assert elapsed >= 2.0
        
        # Scraper should have been called twice
        assert mock_scraper.run.call_count == 2


class TestParallelExecution:
    """Test parallel execution across different domains."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_different_domains(self, mock_db, mock_job, mock_sources):
        """Test that different-domain scrapers run in parallel."""
        # Mock the job query to return our mock_job
        mock_job_query = Mock()
        mock_job_query.filter.return_value = mock_job_query
        mock_job_query.first.return_value = mock_job
        
        # Mock the sources query to return mock_sources
        mock_source_query = Mock()
        mock_source_query.filter.return_value = mock_source_query
        mock_source_query.all.return_value = mock_sources
        
        # Mock the google_maps query to return None (not active)
        mock_google_maps_query = Mock()
        mock_google_maps_query.filter.return_value = mock_google_maps_query
        mock_google_maps_query.first.return_value = None
        
        # Track query call count to return different mocks
        query_call_count = [0]
        
        # Configure mock_db.query to return appropriate query based on model type and call order
        def query_side_effect(model):
            if model.__name__ == 'ScrapeJob':
                return mock_job_query
            elif model.__name__ == 'Source':
                query_call_count[0] += 1
                # First Source query is for category sources, second is for google_maps
                if query_call_count[0] == 1:
                    return mock_source_query
                else:
                    return mock_google_maps_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.run = AsyncMock(return_value=[{"name": "Hotel 1"}])
        
        orchestrator = ScraperOrchestrator()
        
        with patch('scrapers.orchestrator.get_scraper', return_value=mock_scraper):
            start_time = asyncio.get_event_loop().time()
            results, failures = await orchestrator.run_async(mock_db, mock_job.id)
            end_time = asyncio.get_event_loop().time()
        
        # Should have results from all sources
        assert len(results) == 3
        assert len(failures) == 0
        
        # Should take less time than sequential (2 domains in parallel)
        # booking.com has 2 sources (2s delay) + agoda.com has 1 source (0s delay)
        # If parallel: ~2s, if sequential: ~4s
        elapsed = end_time - start_time
        assert elapsed < 4.0  # Should be faster than sequential


class TestFailureTracking:
    """Test failure tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_failure_tracking_scraper_exception(self, mock_db, mock_job):
        """Test that scraper exceptions are tracked as failures."""
        source = Mock(spec=Source)
        source.id = 1
        source.name = "booking_com"
        source.base_url = "https://www.booking.com"
        
        # Mock scraper that raises exception
        mock_scraper = Mock()
        mock_scraper.run = AsyncMock(side_effect=Exception("Scraper failed"))
        
        orchestrator = ScraperOrchestrator()
        
        with patch('scrapers.orchestrator.get_scraper', return_value=mock_scraper):
            results, failures = await orchestrator._run_domain_group(
                mock_db, mock_job, "booking.com", [source]
            )
        
        # Should have no results but one failure
        assert len(results) == 0
        assert len(failures) == 1
        assert failures[0] == 1
    
    @pytest.mark.asyncio
    async def test_failure_tracking_scraper_not_found(self, mock_db, mock_job):
        """Test that missing scrapers are tracked as failures."""
        source = Mock(spec=Source)
        source.id = 1
        source.name = "unknown_scraper"
        source.base_url = "https://www.example.com"
        
        orchestrator = ScraperOrchestrator()
        
        with patch('scrapers.orchestrator.get_scraper', side_effect=ValueError("Unknown scraper")):
            results, failures = await orchestrator._run_domain_group(
                mock_db, mock_job, "example.com", [source]
            )
        
        # Should have no results but one failure
        assert len(results) == 0
        assert len(failures) == 1
        assert failures[0] == 1


class TestPartialSuccess:
    """Test partial success handling."""
    
    @pytest.mark.asyncio
    async def test_partial_success_some_scrapers_fail(self, mock_db, mock_job):
        """Test that job continues when some scrapers fail."""
        source1 = Mock(spec=Source)
        source1.id = 1
        source1.name = "booking_com"
        source1.base_url = "https://www.booking.com"
        
        source2 = Mock(spec=Source)
        source2.id = 2
        source2.name = "agoda"
        source2.base_url = "https://www.agoda.com"
        
        # Mock scraper: first succeeds, second fails
        mock_scraper1 = Mock()
        mock_scraper1.run = AsyncMock(return_value=[{"name": "Hotel 1"}])
        
        mock_scraper2 = Mock()
        mock_scraper2.run = AsyncMock(side_effect=Exception("Failed"))
        
        orchestrator = ScraperOrchestrator()
        
        def get_scraper_side_effect(name):
            if name == "booking_com":
                return mock_scraper1
            else:
                return mock_scraper2
        
        with patch('scrapers.orchestrator.get_scraper', side_effect=get_scraper_side_effect):
            results, failures = await orchestrator._run_domain_group(
                mock_db, mock_job, "test.com", [source1, source2]
            )
        
        # Should have results from successful scraper
        assert len(results) == 1
        assert results[0]["name"] == "Hotel 1"
        
        # Should have failure from failed scraper
        assert len(failures) == 1
        assert failures[0] == 2
    
    @pytest.mark.asyncio
    async def test_partial_success_empty_results_not_failure(self, mock_db, mock_job):
        """Test that empty results are not counted as failures."""
        source = Mock(spec=Source)
        source.id = 1
        source.name = "booking_com"
        source.base_url = "https://www.booking.com"
        
        # Mock scraper that returns empty list (not an exception)
        mock_scraper = Mock()
        mock_scraper.run = AsyncMock(return_value=[])
        
        orchestrator = ScraperOrchestrator()
        
        with patch('scrapers.orchestrator.get_scraper', return_value=mock_scraper):
            results, failures = await orchestrator._run_domain_group(
                mock_db, mock_job, "booking.com", [source]
            )
        
        # Should have no results and no failures (empty is not failure)
        assert len(results) == 0
        assert len(failures) == 0


class TestLoadSources:
    """Test source loading functionality."""
    
    def test_load_sources_all_active(self, mock_db, mock_job, mock_sources):
        """Test loading all active sources for category."""
        # Mock the main query for category sources
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_sources
        
        # Mock the google_maps query to return None (not active)
        mock_google_maps_query = Mock()
        mock_google_maps_query.filter.return_value = mock_google_maps_query
        mock_google_maps_query.first.return_value = None
        
        # Setup db.query to return different mocks for different calls
        mock_db.query.side_effect = [mock_query, mock_google_maps_query]
        
        orchestrator = ScraperOrchestrator()
        sources = orchestrator._load_sources(mock_db, mock_job)
        
        assert len(sources) == 3
        assert all(s.is_active for s in sources)
    
    def test_load_sources_specific_ids(self, mock_db, mock_job, mock_sources):
        """Test loading specific source IDs."""
        mock_job.source_ids = [1, 2]
        
        # Mock the main query for specific source IDs
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_sources[0], mock_sources[1]]
        
        # Mock the google_maps query to return None (not active)
        mock_google_maps_query = Mock()
        mock_google_maps_query.filter.return_value = mock_google_maps_query
        mock_google_maps_query.first.return_value = None
        
        # Setup db.query to return different mocks for different calls
        mock_db.query.side_effect = [mock_query, mock_google_maps_query]
        
        orchestrator = ScraperOrchestrator()
        sources = orchestrator._load_sources(mock_db, mock_job)
        
        assert len(sources) == 2
        assert sources[0].id in [1, 2]
        assert sources[1].id in [1, 2]
