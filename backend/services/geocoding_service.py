"""
Geocoding service using OpenStreetMap Overpass API.

This service converts addresses to geographic coordinates (latitude/longitude)
using the Overpass API and caches results to minimize API calls.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Tuple
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from models.geocoding_cache import GeocodingCache as GeocodingCacheModel
from config import settings

logger = logging.getLogger(__name__)


class Coordinates:
    """Represents geographic coordinates."""
    
    def __init__(self, lat: float, lng: float, source: str = "overpass", confidence: float = 1.0):
        self.lat = lat
        self.lng = lng
        self.source = source
        self.confidence = confidence
    
    def __repr__(self):
        return f"Coordinates(lat={self.lat}, lng={self.lng}, source={self.source})"
    
    def __eq__(self, other):
        if not isinstance(other, Coordinates):
            return False
        return self.lat == other.lat and self.lng == other.lng


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    async def wait(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()


class GeocodingCache:
    """Cache for geocoding results."""
    
    def __init__(self, db: Session):
        self.db = db
        self.hit_count = 0
        self.miss_count = 0
    
    def _make_location_key(self, address: str, city: str, country: str = "Nepal") -> str:
        """Create a unique location key from address, city, and country."""
        return f"{address}|{city}|{country}".lower().strip()
    
    def get(self, address: str, city: str, country: str = "Nepal") -> Optional[Coordinates]:
        """Get cached coordinates for an address."""
        try:
            location_key = self._make_location_key(address, city, country)
            cache_entry = self.db.query(GeocodingCacheModel).filter(
                GeocodingCacheModel.location_name == location_key
            ).first()
            
            if cache_entry and cache_entry.latitude and cache_entry.longitude:
                self.hit_count += 1
                logger.debug(f"Cache hit for {address}, {city}")
                return Coordinates(
                    lat=float(cache_entry.latitude),
                    lng=float(cache_entry.longitude),
                    source=cache_entry.source or "overpass",
                    confidence=float(cache_entry.confidence) if cache_entry.confidence else 1.0
                )
            
            self.miss_count += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, address: str, city: str, coords: Coordinates, country: str = "Nepal"):
        """Store coordinates in cache."""
        try:
            location_key = self._make_location_key(address, city, country)
            
            # Check if entry exists
            cache_entry = self.db.query(GeocodingCacheModel).filter(
                GeocodingCacheModel.location_name == location_key
            ).first()
            
            if cache_entry:
                # Update existing
                cache_entry.address = address
                cache_entry.city = city
                cache_entry.country = country
                cache_entry.latitude = coords.lat
                cache_entry.longitude = coords.lng
                cache_entry.source = coords.source
                cache_entry.confidence = coords.confidence
            else:
                # Create new
                cache_entry = GeocodingCacheModel(
                    location_name=location_key,
                    address=address,
                    city=city,
                    country=country,
                    latitude=coords.lat,
                    longitude=coords.lng,
                    source=coords.source,
                    confidence=coords.confidence
                )
                self.db.add(cache_entry)
            
            self.db.commit()
            logger.debug(f"Cached coordinates for {address}, {city}")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.db.rollback()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0


class GeocodingService:
    """Service for geocoding addresses using Overpass API."""
    
    # Nepal bounding box (approximate)
    NEPAL_BOUNDS = {
        "min_lat": 26.0,
        "max_lat": 31.0,
        "min_lng": 80.0,
        "max_lng": 89.0
    }
    
    # City center coordinates (fallback)
    CITY_CENTERS = {
        "kathmandu": Coordinates(27.7172, 85.3240, source="city_center", confidence=0.5),
        "pokhara": Coordinates(28.2096, 83.9856, source="city_center", confidence=0.5),
        "lalitpur": Coordinates(27.6667, 85.3167, source="city_center", confidence=0.5),
        "biratnagar": Coordinates(26.4525, 87.2718, source="city_center", confidence=0.5),
        "bharatpur": Coordinates(27.6767, 84.4362, source="city_center", confidence=0.5),
    }
    
    def __init__(self, api_url: str = None, timeout: float = None, rate_limit: float = None):
        self.api_url = api_url or settings.OVERPASS_API_URL
        self.timeout = timeout or settings.GEOCODING_TIMEOUT
        rate_limit = rate_limit or settings.GEOCODING_RATE_LIMIT
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit)
    
    def _build_overpass_query(self, address: str, city: str, country: str = "Nepal") -> str:
        """Build Overpass QL query for address lookup."""
        # Escape quotes in address
        address_escaped = address.replace('"', '\\"')
        city_escaped = city.replace('"', '\\"')
        
        query = f"""
        [out:json][timeout:5];
        area["name"="{country}"]->.country;
        (
          node["addr:full"~"{address_escaped}",i](area.country);
          way["addr:full"~"{address_escaped}",i](area.country);
          node["name"~"{address_escaped}",i]["tourism"="hotel"](area.country);
          node["name"~"{address_escaped}",i]["amenity"="hotel"](area.country);
        );
        out center 1;
        """
        return query.strip()
    
    async def _query_overpass(self, query: str) -> Optional[Dict]:
        """Query Overpass API with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Respect rate limit
                await self.rate_limiter.wait()
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.api_url,
                        data={"data": query},
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data
                    elif response.status_code == 429:
                        # Rate limited
                        wait_time = 2 ** attempt * 5  # Exponential backoff
                        logger.warning(f"Rate limited by Overpass API, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code == 406:
                        # Not Acceptable - don't retry, return None immediately
                        logger.error(f"Overpass API returned 406 Not Acceptable - skipping retries")
                        return None
                    else:
                        logger.error(f"Overpass API error: {response.status_code}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"Overpass API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"Overpass API error: {e}")
                return None
        
        return None
    
    def _validate_coords(self, lat: float, lng: float, country: str = "Nepal") -> bool:
        """Validate that coordinates are within expected bounds."""
        if country == "Nepal":
            return (
                self.NEPAL_BOUNDS["min_lat"] <= lat <= self.NEPAL_BOUNDS["max_lat"] and
                self.NEPAL_BOUNDS["min_lng"] <= lng <= self.NEPAL_BOUNDS["max_lng"]
            )
        return True  # Accept any coordinates for other countries
    
    def _get_city_center(self, city: str, country: str = "Nepal") -> Optional[Coordinates]:
        """Get city center coordinates as fallback."""
        city_lower = city.lower().strip()
        
        if city_lower in self.CITY_CENTERS:
            logger.info(f"Using city center for {city}")
            return self.CITY_CENTERS[city_lower]
        
        # Default to Kathmandu if city not found
        logger.warning(f"City {city} not found, using Kathmandu as fallback")
        return self.CITY_CENTERS["kathmandu"]
    
    async def geocode_address(
        self,
        address: str,
        city: str,
        country: str = "Nepal",
        use_cache: bool = True
    ) -> Optional[Coordinates]:
        """
        Geocode an address to coordinates.
        
        Args:
            address: Street address or hotel name
            city: City name
            country: Country name (default: Nepal)
            use_cache: Whether to use cache (default: True)
        
        Returns:
            Coordinates object or None if geocoding fails
        """
        if not address or not city:
            logger.warning("Address or city is empty")
            return None
        
        # Check cache first
        if use_cache:
            db = SessionLocal()
            try:
                cache = GeocodingCache(db)
                cached = cache.get(address, city, country)
                if cached:
                    return cached
            finally:
                db.close()
        
        # Query Overpass API
        query = self._build_overpass_query(address, city, country)
        data = await self._query_overpass(query)
        
        if not data or "elements" not in data or len(data["elements"]) == 0:
            logger.info(f"No results from Overpass for {address}, {city}")
            # Fall back to city center
            fallback_coords = self._get_city_center(city, country)
            
            # Cache the fallback coordinates to avoid repeated Overpass queries
            if use_cache and fallback_coords:
                db = SessionLocal()
                try:
                    cache = GeocodingCache(db)
                    cache.set(address, city, fallback_coords, country)
                finally:
                    db.close()
            
            return fallback_coords
        
        # Extract coordinates from first result
        element = data["elements"][0]
        
        if "lat" in element and "lon" in element:
            lat = float(element["lat"])
            lng = float(element["lon"])
        elif "center" in element:
            lat = float(element["center"]["lat"])
            lng = float(element["center"]["lon"])
        else:
            logger.warning(f"No coordinates in Overpass response for {address}")
            return self._get_city_center(city, country)
        
        # Validate coordinates
        if not self._validate_coords(lat, lng, country):
            logger.warning(f"Coordinates out of bounds: {lat}, {lng}")
            fallback_coords = self._get_city_center(city, country)
            
            # Cache the fallback coordinates
            if use_cache and fallback_coords:
                db = SessionLocal()
                try:
                    cache = GeocodingCache(db)
                    cache.set(address, city, fallback_coords, country)
                finally:
                    db.close()
            
            return fallback_coords
        
        coords = Coordinates(lat, lng, source="overpass", confidence=0.9)
        
        # Cache the result
        if use_cache:
            db = SessionLocal()
            try:
                cache = GeocodingCache(db)
                cache.set(address, city, coords, country)
            finally:
                db.close()
        
        logger.info(f"Geocoded {address}, {city} to {lat}, {lng}")
        return coords
    
    async def geocode_batch(
        self,
        addresses: list[Dict[str, str]],
        use_cache: bool = True
    ) -> list[Optional[Coordinates]]:
        """
        Batch geocode multiple addresses.
        
        Args:
            addresses: List of dicts with 'address', 'city', 'country' keys
            use_cache: Whether to use cache (default: True)
        
        Returns:
            List of Coordinates or None for each address
        """
        results = []
        
        for addr_dict in addresses:
            address = addr_dict.get("address", "")
            city = addr_dict.get("city", "")
            country = addr_dict.get("country", "Nepal")
            
            coords = await self.geocode_address(address, city, country, use_cache)
            results.append(coords)
        
        return results


# Global service instance
geocoding_service = GeocodingService()
