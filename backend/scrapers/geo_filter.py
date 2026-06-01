"""Geographic boundary filtering for Nepal cities.

Removes results that fall outside city boundaries.

Boundaries defined using bounding boxes.
Each city has lat/lon min/max that covers the
administrative area plus a small buffer (0.02°)
to avoid removing legitimate border businesses.

1 degree latitude ≈ 111 km
1 degree longitude ≈ 89 km (at Nepal's latitude)
Buffer of 0.02° ≈ 1.8-2.2 km
"""

from typing import Optional
import structlog

logger = structlog.get_logger()

# City bounding boxes with small buffer
# Format: (lat_min, lat_max, lon_min, lon_max)
# Verified against Google Maps boundaries and actual DB data
CITY_BOUNDARIES = {
    "kathmandu": (27.62, 27.78, 85.26, 85.40),
    "lalitpur": (27.63, 27.72, 85.29, 85.37),
    "bhaktapur": (27.64, 27.73, 85.38, 85.47),
    "pokhara": (28.14, 28.29, 83.87, 84.09),
    "biratnagar": (26.39, 26.53, 87.23, 87.32),
    "birgunj": (26.97, 27.08, 84.81, 84.95),
    "chitwan": (27.48, 27.60, 84.30, 84.44),
    "butwal": (27.56, 27.74, 83.08, 83.55),
    "dharan": (26.65, 26.87, 87.25, 87.34),
    "hetauda": (27.40, 27.46, 84.98, 85.07),
    "nepalgunj": (28.02, 28.08, 81.59, 81.65),
    "dhangadhi": (28.66, 28.72, 80.57, 80.63),
    "janakpur": (26.70, 26.76, 85.91, 85.97),
    "itahari": (26.64, 26.70, 87.26, 87.32),
    "bharatpur": (27.18, 27.72, 84.40, 84.48),
}


def is_within_city(
    lat: Optional[float],
    lon: Optional[float],
    city: str,
) -> bool:
    """Check if coordinates fall within city boundary.
    
    Returns True if:
    - Coordinates are within bounding box, OR
    - No coordinates available (can't filter), OR
    - City not in our boundary database
    
    Returns False only if coordinates exist AND
    fall clearly outside the city boundary.
    """
    # If no coordinates, can't filter — keep result
    if lat is None or lon is None:
        return True
    
    city_lower = city.lower().strip()
    
    # If city not in our database, can't filter
    if city_lower not in CITY_BOUNDARIES:
        return True
    
    lat_min, lat_max, lon_min, lon_max = CITY_BOUNDARIES[city_lower]
    
    return (lat_min <= lat <= lat_max and
            lon_min <= lon <= lon_max)


def filter_results_by_city(
    results: list[dict],
    city: str,
    strict: bool = False,
) -> tuple[list[dict], int]:
    """Filter scraping results to only include
    businesses within the target city.
    
    Args:
        results: List of scraped business dicts
        city: Target city name
        strict: If True, remove results without
                coordinates. If False (default),
                keep results without coordinates.
    
    Returns:
        (filtered_results, removed_count)
    """
    if not results:
        return results, 0
    
    city_lower = city.lower().strip()
    
    # If city not in boundaries, skip filtering
    if city_lower not in CITY_BOUNDARIES:
        logger.info(
            "geo_filter.city_not_found",
            city=city,
            message="City not in boundary database, skipping filter"
        )
        return results, 0
    
    filtered = []
    removed = 0
    no_coords = 0
    
    for result in results:
        lat = result.get("latitude")
        lon = result.get("longitude")
        
        # Handle results without coordinates
        if lat is None or lon is None:
            no_coords += 1
            if not strict:
                # Keep results without coordinates
                # They might be in the right city
                filtered.append(result)
            else:
                removed += 1
            continue
        
        if is_within_city(lat, lon, city_lower):
            filtered.append(result)
        else:
            removed += 1
            logger.debug(
                "geo_filter.removed",
                name=result.get("name", "unknown"),
                lat=lat,
                lon=lon,
                city=city,
                reason="outside_boundary"
            )
    
    if removed > 0:
        logger.info(
            "geo_filter.applied",
            city=city,
            original_count=len(results),
            filtered_count=len(filtered),
            removed_count=removed,
            no_coords_count=no_coords,
            removal_rate=round(removed / len(results) * 100, 1)
        )
    
    return filtered, removed


def get_city_center(city: str) -> Optional[tuple]:
    """Get center coordinates for a city.
    
    Returns (lat, lon) or None if city unknown.
    """
    city_lower = city.lower().strip()
    
    if city_lower not in CITY_BOUNDARIES:
        return None
    
    lat_min, lat_max, lon_min, lon_max = CITY_BOUNDARIES[city_lower]
    
    return (
        (lat_min + lat_max) / 2,
        (lon_min + lon_max) / 2
    )
