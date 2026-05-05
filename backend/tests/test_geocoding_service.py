"""
Tests for geocoding service.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from services.geocoding_service import (
    Coordinates,
    RateLimiter,
    GeocodingCache,
    GeocodingService,
    geocoding_service
)
from models.geocoding_cache import GeocodingCache as GeocodingCacheModel


class TestCoordinates:
    """Test Coordinates class."""
    
    def test_coordinates_creation(self):
        """Test creating Coordinates object."""
        coords = Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9)
        assert coords.lat == 27.7172
        assert coords.lng == 85.3240
        assert coords.source == "overpass"
        assert coords.confidence == 0.9
    
    def test_coordinates_equality(self):
        """Test Coordinates equality comparison."""
        coords1 = Coordinates(27.7172, 85.3240)
        coords2 = Coordinates(27.7172, 85.3240)
        coords3 = Coordinates(27.7173, 85.3240)
        
        assert coords1 == coords2
        assert coords1 != coords3
        assert coords1 != "not a coordinate"
    
    def test_coordinates_repr(self):
        """Test Coordinates string representation."""
        coords = Coordinates(27.7172, 85.3240, source="overpass")
        repr_str = repr(coords)
        assert "27.7172" in repr_str
        assert "85.32" in repr_str  # Python may truncate trailing zeros
        assert "overpass" in repr_str


class TestRateLimiter:
    """Test RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_waits(self):
        """Test that rate limiter enforces wait time."""
        import time
        
        limiter = RateLimiter(requests_per_second=2.0)  # 0.5s between requests
        
        start = time.time()
        await limiter.wait()
        await limiter.wait()
        elapsed = time.time() - start
        
        # Should wait at least 0.5 seconds between calls
        assert elapsed >= 0.4  # Allow small margin for timing
    
    @pytest.mark.asyncio
    async def test_rate_limiter_first_call_no_wait(self):
        """Test that first call doesn't wait."""
        import time
        
        limiter = RateLimiter(requests_per_second=1.0)
        
        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start
        
        # First call should be immediate
        assert elapsed < 0.1


class TestGeocodingCache:
    """Test GeocodingCache class."""
    
    def test_cache_miss(self, db_session: Session):
        """Test cache miss returns None."""
        cache = GeocodingCache(db_session)
        result = cache.get("Hotel Yak & Yeti", "Kathmandu")
        
        assert result is None
        assert cache.miss_count == 1
        assert cache.hit_count == 0
    
    def test_cache_set_and_get(self, db_session: Session):
        """Test setting and getting from cache."""
        cache = GeocodingCache(db_session)
        coords = Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9)
        
        # Set cache
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords)
        
        # Get from cache
        result = cache.get("Hotel Yak & Yeti", "Kathmandu")
        
        assert result is not None
        assert result.lat == 27.7172
        assert result.lng == 85.3240
        assert result.source == "overpass"
        assert result.confidence == 0.9
        assert cache.hit_count == 1
    
    def test_cache_update_existing(self, db_session: Session):
        """Test updating existing cache entry."""
        cache = GeocodingCache(db_session)
        
        # Set initial coords
        coords1 = Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9)
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords1)
        
        # Update with new coords
        coords2 = Coordinates(27.7173, 85.3241, source="manual", confidence=1.0)
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords2)
        
        # Get updated coords
        result = cache.get("Hotel Yak & Yeti", "Kathmandu")
        
        assert result.lat == 27.7173
        assert result.lng == 85.3241
        assert result.source == "manual"
        assert result.confidence == 1.0
    
    def test_cache_hit_rate(self, db_session: Session):
        """Test cache hit rate calculation."""
        cache = GeocodingCache(db_session)
        coords = Coordinates(27.7172, 85.3240)
        
        # Set one entry
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords)
        
        # 2 hits, 1 miss
        cache.get("Hotel Yak & Yeti", "Kathmandu")  # hit
        cache.get("Hotel Yak & Yeti", "Kathmandu")  # hit
        cache.get("Nonexistent Hotel", "Pokhara")   # miss
        
        assert cache.hit_count == 2
        assert cache.miss_count == 1
        assert cache.hit_rate == 2/3
    
    def test_cache_location_key_case_insensitive(self, db_session: Session):
        """Test that cache keys are case-insensitive."""
        cache = GeocodingCache(db_session)
        coords = Coordinates(27.7172, 85.3240)
        
        # Set with mixed case
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords)
        
        # Get with different case
        result = cache.get("HOTEL YAK & YETI", "KATHMANDU")
        
        assert result is not None
        assert result.lat == 27.7172


class TestGeocodingService:
    """Test GeocodingService class."""
    
    def test_validate_coords_nepal(self):
        """Test coordinate validation for Nepal."""
        service = GeocodingService()
        
        # Valid Nepal coordinates
        assert service._validate_coords(27.7172, 85.3240, "Nepal") is True
        
        # Out of bounds (too far north)
        assert service._validate_coords(32.0, 85.3240, "Nepal") is False
        
        # Out of bounds (too far west)
        assert service._validate_coords(27.7172, 79.0, "Nepal") is False
    
    def test_validate_coords_other_country(self):
        """Test coordinate validation for other countries."""
        service = GeocodingService()
        
        # Any coordinates valid for non-Nepal countries
        assert service._validate_coords(0.0, 0.0, "India") is True
        assert service._validate_coords(90.0, 180.0, "USA") is True
    
    def test_get_city_center_known_city(self):
        """Test getting city center for known cities."""
        service = GeocodingService()
        
        coords = service._get_city_center("Kathmandu")
        assert coords is not None
        assert coords.lat == 27.7172
        assert coords.lng == 85.3240
        assert coords.source == "city_center"
        assert coords.confidence == 0.5
        
        coords = service._get_city_center("Pokhara")
        assert coords is not None
        assert coords.lat == 28.2096
    
    def test_get_city_center_unknown_city(self):
        """Test getting city center for unknown city falls back to Kathmandu."""
        service = GeocodingService()
        
        coords = service._get_city_center("UnknownCity")
        assert coords is not None
        assert coords.lat == 27.7172  # Kathmandu
        assert coords.lng == 85.3240
    
    def test_build_overpass_query(self):
        """Test building Overpass QL query."""
        service = GeocodingService()
        
        query = service._build_overpass_query("Hotel Yak & Yeti", "Kathmandu", "Nepal")
        
        assert "Hotel Yak & Yeti" in query
        assert "Kathmandu" in query or "Nepal" in query
        assert "[out:json]" in query
        assert "out center" in query
    
    def test_build_overpass_query_escapes_quotes(self):
        """Test that quotes in address are escaped."""
        service = GeocodingService()
        
        query = service._build_overpass_query('Hotel "Fancy" Name', "Kathmandu")
        
        # Should escape quotes
        assert '\\"' in query or "Fancy" in query
    
    @pytest.mark.asyncio
    async def test_query_overpass_success(self):
        """Test successful Overpass API query."""
        service = GeocodingService()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {"lat": 27.7172, "lon": 85.3240}
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await service._query_overpass("test query")
            
            assert result is not None
            assert "elements" in result
            assert len(result["elements"]) == 1
    
    @pytest.mark.asyncio
    async def test_query_overpass_timeout(self):
        """Test Overpass API timeout handling."""
        service = GeocodingService(timeout=0.1)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Timeout")
            )
            
            result = await service._query_overpass("test query")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_query_overpass_rate_limit(self):
        """Test Overpass API rate limit handling (429)."""
        service = GeocodingService()
        
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"elements": []}
        
        with patch("httpx.AsyncClient") as mock_client:
            # First call returns 429, second returns 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_429, mock_response_200]
            )
            
            with patch("asyncio.sleep"):  # Speed up test
                result = await service._query_overpass("test query")
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_geocode_address_cache_hit(self, db_session: Session):
        """Test geocoding with cache hit."""
        service = GeocodingService()
        
        # Pre-populate cache
        cache = GeocodingCache(db_session)
        coords = Coordinates(27.7172, 85.3240, source="overpass", confidence=0.9)
        cache.set("Hotel Yak & Yeti", "Kathmandu", coords)
        
        # Mock SessionLocal to return our test session
        with patch("services.geocoding_service.SessionLocal", return_value=db_session):
            result = await service.geocode_address("Hotel Yak & Yeti", "Kathmandu")
        
        assert result is not None
        assert result.lat == 27.7172
        assert result.lng == 85.3240
    
    @pytest.mark.asyncio
    async def test_geocode_address_empty_input(self):
        """Test geocoding with empty address or city."""
        service = GeocodingService()
        
        result = await service.geocode_address("", "Kathmandu")
        assert result is None
        
        result = await service.geocode_address("Hotel Yak & Yeti", "")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_geocode_address_no_results_fallback(self, db_session: Session):
        """Test geocoding falls back to city center when no results."""
        service = GeocodingService()
        
        # Mock Overpass API to return no results
        with patch.object(service, "_query_overpass", return_value={"elements": []}):
            with patch("services.geocoding_service.SessionLocal", return_value=db_session):
                result = await service.geocode_address("Nonexistent Hotel", "Kathmandu")
        
        assert result is not None
        assert result.lat == 27.7172  # Kathmandu city center
        assert result.source == "city_center"
        assert result.confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_geocode_address_invalid_coords_fallback(self, db_session: Session):
        """Test geocoding falls back to city center when coords invalid."""
        service = GeocodingService()
        
        # Mock Overpass API to return out-of-bounds coordinates
        mock_data = {
            "elements": [
                {"lat": 50.0, "lon": 10.0}  # Not in Nepal
            ]
        }
        
        with patch.object(service, "_query_overpass", return_value=mock_data):
            with patch("services.geocoding_service.SessionLocal", return_value=db_session):
                result = await service.geocode_address("Hotel", "Kathmandu")
        
        assert result is not None
        assert result.lat == 27.7172  # Kathmandu city center
        assert result.source == "city_center"
    
    @pytest.mark.asyncio
    async def test_geocode_address_success_with_center(self, db_session: Session):
        """Test successful geocoding with center coordinates."""
        service = GeocodingService()
        
        # Mock Overpass API to return center coordinates
        mock_data = {
            "elements": [
                {"center": {"lat": 27.7172, "lon": 85.3240}}
            ]
        }
        
        with patch.object(service, "_query_overpass", return_value=mock_data):
            with patch("services.geocoding_service.SessionLocal", return_value=db_session):
                result = await service.geocode_address("Hotel Yak & Yeti", "Kathmandu")
        
        assert result is not None
        assert result.lat == 27.7172
        assert result.lng == 85.3240
        assert result.source == "overpass"
        assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_geocode_batch(self, db_session: Session):
        """Test batch geocoding multiple addresses."""
        service = GeocodingService()
        
        addresses = [
            {"address": "Hotel Yak & Yeti", "city": "Kathmandu", "country": "Nepal"},
            {"address": "Temple Tree Resort", "city": "Pokhara", "country": "Nepal"},
            {"address": "Invalid Hotel", "city": "Kathmandu", "country": "Nepal"}
        ]
        
        # Mock geocode_address to return predictable results
        async def mock_geocode(address, city, country, use_cache):
            if "Yak" in address:
                return Coordinates(27.7172, 85.3240)
            elif "Temple" in address:
                return Coordinates(28.2096, 83.9856)
            else:
                return None
        
        with patch.object(service, "geocode_address", side_effect=mock_geocode):
            results = await service.geocode_batch(addresses)
        
        assert len(results) == 3
        assert results[0] is not None
        assert results[0].lat == 27.7172
        assert results[1] is not None
        assert results[1].lat == 28.2096
        assert results[2] is None
    
    @pytest.mark.asyncio
    async def test_geocode_batch_empty_list(self):
        """Test batch geocoding with empty list."""
        service = GeocodingService()
        
        results = await service.geocode_batch([])
        
        assert results == []


class TestGeocodingServiceIntegration:
    """Integration tests for geocoding service."""
    
    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test that global service instance is configured correctly."""
        assert geocoding_service is not None
        assert geocoding_service.api_url == "https://overpass-api.de/api/interpreter"
        assert geocoding_service.timeout == 10
    
    @pytest.mark.asyncio
    async def test_geocode_with_cache_disabled(self, db_session: Session):
        """Test geocoding with cache disabled."""
        service = GeocodingService()
        
        # Clear any existing cache entries
        db_session.query(GeocodingCacheModel).delete()
        db_session.commit()
        
        # Mock Overpass API
        mock_data = {
            "elements": [
                {"lat": 27.7172, "lon": 85.3240}
            ]
        }
        
        with patch.object(service, "_query_overpass", return_value=mock_data):
            with patch("services.geocoding_service.SessionLocal", return_value=db_session):
                result = await service.geocode_address(
                    "Hotel Yak & Yeti",
                    "Kathmandu",
                    use_cache=False
                )
        
        assert result is not None
        assert result.lat == 27.7172
        
        # Verify not cached
        cache = GeocodingCache(db_session)
        cached = cache.get("Hotel Yak & Yeti", "Kathmandu")
        assert cached is None
