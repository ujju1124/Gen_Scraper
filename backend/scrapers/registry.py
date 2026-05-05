"""
Scraper Registry for Web Scraping Portal Phase 2 & Phase 4B

This module provides a simple registry for mapping source names to scraper classes.
Adding a new scraper requires only adding one line to the registry dict.
"""

import structlog
from scrapers.booking_com import BookingComScraper
from scrapers.agoda import AgodaScraper
from scrapers.oyo_rooms import OYORoomsScraper
from scrapers.esewa_hotels import ESewaHotelsScraper
from scrapers.nepalyp import NepalYPScraper
from scrapers.hostelworld import HostelworldScraper
from scrapers.directoryofnepal import DirectoryOfNepalScraper
from scrapers.foodmandu import FoodmanduScraper
from scrapers.google_maps import GoogleMapsScraper

logger = structlog.get_logger()

# Simple dict mapping source names to scraper classes
registry = {
    "booking_com": BookingComScraper,
    "agoda": AgodaScraper,
    "oyo_rooms": OYORoomsScraper,
    "esewa_hotels": ESewaHotelsScraper,
    "nepalyp": NepalYPScraper,
    "hostelworld": HostelworldScraper,
    "directoryofnepal_hotels": DirectoryOfNepalScraper,
    "foodmandu": FoodmanduScraper,
    "nepalyp_restaurants": NepalYPScraper,
    "directoryofnepal_restaurants": DirectoryOfNepalScraper,
    "nepalyp_pharmacies": NepalYPScraper,
    "nepalyp_drugstores": NepalYPScraper,
    "directoryofnepal_pharmacies": DirectoryOfNepalScraper,
    "nepalyp_hospitals": NepalYPScraper,
    "nepalyp_banks": NepalYPScraper,
    "nepalyp_schools": NepalYPScraper,
    "nepalyp_colleges": NepalYPScraper,
    "nepalyp_travel_agents": NepalYPScraper,
    "nepalyp_tour_operators": NepalYPScraper,
    "nepalyp_shopping_centres": NepalYPScraper,
    "nepalyp_clinics": NepalYPScraper,
    "nepalyp_car_rental": NepalYPScraper,
    "nepalyp_bakers": NepalYPScraper,
    "nepalyp_insurance": NepalYPScraper,
    "nepalyp_real_estate": NepalYPScraper,
    "nepalyp_petrol_stations": NepalYPScraper,
    "nepalyp_motorcycle_dealers": NepalYPScraper,
    "nepalyp_tourist_attractions": NepalYPScraper,
    "nepalyp_homestays": NepalYPScraper,
    "nepalyp_resorts": NepalYPScraper,
    "nepalyp_courier": NepalYPScraper,
    "google_maps": GoogleMapsScraper,
}


def get_scraper(source_name: str):
    """
    Get scraper instance by source name.
    
    Args:
        source_name: Name of the source (e.g., "booking_com")
        
    Returns:
        Instance of the scraper class
        
    Raises:
        ValueError: If source name is not found in registry
        
    Example:
        >>> scraper = get_scraper("booking_com")
        >>> results = await scraper.run(source, db, location)
    """
    scraper_class = registry.get(source_name)
    
    if not scraper_class:
        logger.error(
            "scraper.not_found",
            source_name=source_name,
            available_scrapers=list(registry.keys())
        )
        raise ValueError(
            f"Unknown scraper: {source_name}. "
            f"Available scrapers: {', '.join(registry.keys())}"
        )
    
    logger.debug(
        "scraper.retrieved",
        source_name=source_name,
        scraper_class=scraper_class.__name__
    )
    
    # Try to pass source_name to __init__ if the scraper supports it
    try:
        return scraper_class(source_name=source_name)
    except TypeError:
        # Fallback for scrapers that don't accept source_name parameter
        return scraper_class()


def list_scrapers() -> list[str]:
    """
    List all available scraper names.
    
    Returns:
        List of source names that have scrapers
        
    Example:
        >>> list_scrapers()
        ['booking_com']
    """
    return list(registry.keys())


# How to add a new scraper:
# 1. Create new scraper file (e.g., backend/scrapers/agoda.py)
# 2. Implement scraper class inheriting from BaseScraper
# 3. Import the class at the top of this file
# 4. Add one line to the registry dict above
# 5. Done!
