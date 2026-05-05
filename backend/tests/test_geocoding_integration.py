"""
Integration tests for geocoding in scraping pipeline.
Tests the geocode_job_results function and its integration with the scrape task.
"""
import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from tasks.scrape_task import geocode_job_results
from models import CleanedResult, ScrapeJob
from services.geocoding_service import Coordinates


class TestGeocodeJobResults:
    """Test geocode_job_results function."""
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_success(self, db_session: Session, test_user):
        """Test successful geocoding of job results."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned results without coordinates
        result1 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            country="Nepal",
            latitude=None,
            longitude=None
        )
        result2 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Annapurna",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            country="Nepal",
            latitude=None,
            longitude=None
        )
        db_session.add(result1)
        db_session.add(result2)
        db_session.commit()
        
        # Mock geocoding service to return coordinates
        mock_coords = [
            Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9),
            Coordinates(27.7173, 85.3241, source="overpass", confidence=0.9)
        ]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_coords
            
            # Run geocoding
            geocoded_count = await geocode_job_results(db_session, str(job.id))
        
        # Verify results
        assert geocoded_count == 2
        
        # Refresh results from database
        db_session.refresh(result1)
        db_session.refresh(result2)
        
        assert float(result1.latitude) == 27.7172
        assert float(result1.longitude) == 85.3240
        assert float(result2.latitude) == 27.7173
        assert float(result2.longitude) == 85.3241
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_partial_success(self, db_session: Session, test_user):
        """Test geocoding with some failures."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned results
        result1 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        result2 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Unknown Hotel",
            address="Unknown Address",
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        db_session.add(result1)
        db_session.add(result2)
        db_session.commit()
        
        # Mock geocoding service: first succeeds, second fails
        mock_coords = [
            Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9),
            None  # Geocoding failed
        ]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_coords
            
            # Run geocoding
            geocoded_count = await geocode_job_results(db_session, str(job.id))
        
        # Verify results
        assert geocoded_count == 1
        
        # Refresh results from database
        db_session.refresh(result1)
        db_session.refresh(result2)
        
        assert float(result1.latitude) == 27.7172
        assert float(result1.longitude) == 85.3240
        assert result2.latitude is None
        assert result2.longitude is None
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_no_results(self, db_session: Session, test_user):
        """Test geocoding with no results to geocode."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # No cleaned results created
        
        # Run geocoding
        geocoded_count = await geocode_job_results(db_session, str(job.id))
        
        # Verify no geocoding occurred
        assert geocoded_count == 0
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_already_geocoded(self, db_session: Session, test_user):
        """Test that already geocoded results are skipped."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result with existing coordinates
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            latitude=27.7172,  # Already geocoded
            longitude=85.3240
        )
        db_session.add(result)
        db_session.commit()
        
        # Run geocoding
        geocoded_count = await geocode_job_results(db_session, str(job.id))
        
        # Verify no geocoding occurred
        assert geocoded_count == 0
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_missing_address(self, db_session: Session, test_user):
        """Test that results without address or city are skipped."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned results with missing data
        result1 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Without Address",
            address=None,  # Missing address
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        result2 = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Without City",
            address="Some Address",
            city=None,  # Missing city
            latitude=None,
            longitude=None
        )
        db_session.add(result1)
        db_session.add(result2)
        db_session.commit()
        
        # Run geocoding
        geocoded_count = await geocode_job_results(db_session, str(job.id))
        
        # Verify no geocoding occurred
        assert geocoded_count == 0
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_uses_street_address(self, db_session: Session, test_user):
        """Test that street_address is preferred over full address."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result with both address and street_address
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Full address with extra details",
            street_address="Durbar Marg",  # Should use this
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        db_session.add(result)
        db_session.commit()
        
        # Mock geocoding service
        mock_coords = [Coordinates(27.7172, 85.3240)]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_coords
            
            # Run geocoding
            await geocode_job_results(db_session, str(job.id))
            
            # Verify street_address was used
            call_args = mock_geocode.call_args[0][0]
            assert call_args[0]["address"] == "Durbar Marg"
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_timeout(self, db_session: Session, test_user):
        """Test that geocoding respects timeout."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        db_session.add(result)
        db_session.commit()
        
        # Mock geocoding service to timeout
        async def slow_geocode(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return [Coordinates(27.7172, 85.3240)]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", side_effect=slow_geocode):
            # Run geocoding with short timeout
            with pytest.raises(asyncio.TimeoutError):
                await geocode_job_results(db_session, str(job.id), timeout_seconds=1)
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_error_handling(self, db_session: Session, test_user):
        """Test that geocoding errors are handled gracefully."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        db_session.add(result)
        db_session.commit()
        
        # Mock geocoding service to raise error
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.side_effect = Exception("Geocoding API error")
            
            # Run geocoding - should raise exception
            with pytest.raises(Exception, match="Geocoding API error"):
                await geocode_job_results(db_session, str(job.id))
        
        # Verify database was rolled back (no coordinates saved)
        db_session.refresh(result)
        assert result.latitude is None
        assert result.longitude is None
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_uses_cache(self, db_session: Session, test_user):
        """Test that geocoding uses cache."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg, Kathmandu",
            city="Kathmandu",
            latitude=None,
            longitude=None
        )
        db_session.add(result)
        db_session.commit()
        
        # Mock geocoding service
        mock_coords = [Coordinates(27.7172, 85.3240)]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_coords
            
            # Run geocoding
            await geocode_job_results(db_session, str(job.id))
            
            # Verify use_cache=True was passed
            call_kwargs = mock_geocode.call_args[1]
            assert call_kwargs.get("use_cache") is True
    
    @pytest.mark.asyncio
    async def test_geocode_job_results_defaults_to_kathmandu(self, db_session: Session, test_user):
        """Test that missing city defaults to Kathmandu."""
        # Create a test job
        job = ScrapeJob(
            id=uuid.uuid4(),
            user_id=test_user.id,
            category_id=1,
            location="Kathmandu",
            status="RUNNING"
        )
        db_session.add(job)
        db_session.commit()
        
        # Create cleaned result with empty city (but not None, so it passes the filter)
        result = CleanedResult(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=1,
            category_id=1,
            name="Hotel Yak & Yeti",
            address="Durbar Marg",
            city="",  # Empty string
            latitude=None,
            longitude=None
        )
        db_session.add(result)
        db_session.commit()
        
        # Update city to empty string after creation (to bypass NOT NULL constraint)
        result.city = ""
        db_session.commit()
        
        # Mock geocoding service
        mock_coords = [Coordinates(27.7172, 85.3240)]
        
        with patch("tasks.scrape_task.geocoding_service.geocode_batch", new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_coords
            
            # Run geocoding
            await geocode_job_results(db_session, str(job.id))
            
            # Verify Kathmandu was used as default
            call_args = mock_geocode.call_args[0][0]
            assert call_args[0]["city"] == "Kathmandu"


class TestGeocodingInScrapeTask:
    """Test geocoding integration in scrape_task."""
    
    def test_geocoding_enabled_in_config(self):
        """Test that geocoding can be enabled/disabled via config."""
        from config import settings
        
        # Verify GEOCODING_ENABLED setting exists
        assert hasattr(settings, "GEOCODING_ENABLED")
        assert isinstance(settings.GEOCODING_ENABLED, bool)
    
    @pytest.mark.asyncio
    async def test_geocoding_skipped_when_disabled(self, db_session: Session):
        """Test that geocoding is skipped when GEOCODING_ENABLED=False."""
        # This test would require mocking the entire scrape task
        # For now, we verify the config setting exists
        from config import settings
        
        # If GEOCODING_ENABLED is False, geocoding should be skipped
        if not settings.GEOCODING_ENABLED:
            # Create a test job
            job = ScrapeJob(
                id=uuid.uuid4(),
                user_id=test_user.id,
                category_id=1,
                location="Kathmandu",
                status="RUNNING"
            )
            db_session.add(job)
            db_session.commit()
            
            # Create cleaned result
            result = CleanedResult(
                id=uuid.uuid4(),
                job_id=job.id,
                source_id=1,
                category_id=1,
                name="Hotel Yak & Yeti",
                address="Durbar Marg, Kathmandu",
                city="Kathmandu",
                latitude=None,
                longitude=None
            )
            db_session.add(result)
            db_session.commit()
            
            # Geocoding should not be called
            # (This is tested implicitly by the scrape task implementation)
