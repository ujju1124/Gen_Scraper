"""
Unit tests for NepalYP category support.

These tests verify that NepalYP scraper:
1. Extracts category from source_name correctly
2. Can be reused for multiple categories (Hotels, Restaurants, Pharmacies)
3. Is properly registered for each category variant
"""

import pytest
from scrapers.nepalyp import NepalYPScraper
from scrapers.registry import get_scraper


def test_nepalyp_scraper_default_category():
    """Test that NepalYP scraper defaults to Hotels category."""
    scraper = NepalYPScraper()
    scraper.source_name = "nepalyp"
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Hotels"


def test_nepalyp_scraper_restaurants_category():
    """Test that NepalYP scraper extracts Restaurants category from source_name."""
    scraper = NepalYPScraper()
    scraper.source_name = "nepalyp_restaurants"
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Restaurants"


def test_nepalyp_scraper_pharmacies_category():
    """Test that NepalYP scraper extracts Pharmacies category from source_name."""
    scraper = NepalYPScraper()
    scraper.source_name = "nepalyp_pharmacies"
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Pharmacies"


def test_nepalyp_restaurants_registered_in_registry():
    """Test that nepalyp_restaurants is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_restaurants")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_restaurants"


def test_nepalyp_restaurants_category_extraction():
    """Test that nepalyp_restaurants correctly extracts Restaurants category."""
    scraper = get_scraper("nepalyp_restaurants")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Restaurants"


def test_nepalyp_hotels_still_works():
    """Test that original nepalyp (Hotels) still works after category changes."""
    scraper = get_scraper("nepalyp")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp"
    
    category = scraper._get_category_from_source_name()
    assert category == "Hotels"


def test_nepalyp_category_capitalization():
    """Test that category names are properly capitalized."""
    scraper = NepalYPScraper()
    
    # Test lowercase suffix
    scraper.source_name = "nepalyp_restaurants"
    assert scraper._get_category_from_source_name() == "Restaurants"
    
    scraper.source_name = "nepalyp_pharmacies"
    assert scraper._get_category_from_source_name() == "Pharmacies"



def test_nepalyp_pharmacies_registered_in_registry():
    """Test that nepalyp_pharmacies is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_pharmacies")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_pharmacies"


def test_nepalyp_pharmacies_category_extraction():
    """Test that nepalyp_pharmacies correctly extracts Pharmacies category."""
    scraper = get_scraper("nepalyp_pharmacies")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Pharmacies"


def test_nepalyp_drugstores_registered_in_registry():
    """Test that nepalyp_drugstores is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_drugstores")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_drugstores"


def test_nepalyp_drugstores_category_extraction():
    """Test that nepalyp_drugstores correctly extracts Drugstores category."""
    scraper = get_scraper("nepalyp_drugstores")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Drugstores"


def test_nepalyp_hospitals_registered_in_registry():
    """Test that nepalyp_hospitals is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_hospitals")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_hospitals"


def test_nepalyp_hospitals_category_extraction():
    """Test that nepalyp_hospitals correctly extracts Hospitals category."""
    scraper = get_scraper("nepalyp_hospitals")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Hospitals"


def test_nepalyp_banks_registered_in_registry():
    """Test that nepalyp_banks is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_banks")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_banks"


def test_nepalyp_banks_category_extraction():
    """Test that nepalyp_banks correctly extracts Bankscredit_unions category."""
    scraper = get_scraper("nepalyp_banks")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Bankscredit_unions"


def test_nepalyp_schools_registered_in_registry():
    """Test that nepalyp_schools is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_schools")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_schools"


def test_nepalyp_schools_category_extraction():
    """Test that nepalyp_schools correctly extracts Schools category."""
    scraper = get_scraper("nepalyp_schools")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Schools"


def test_nepalyp_colleges_registered_in_registry():
    """Test that nepalyp_colleges is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_colleges")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_colleges"


def test_nepalyp_colleges_category_extraction():
    """Test that nepalyp_colleges correctly extracts Colleges category."""
    scraper = get_scraper("nepalyp_colleges")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Colleges"


def test_nepalyp_travel_agents_registered_in_registry():
    """Test that nepalyp_travel_agents is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_travel_agents")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_travel_agents"


def test_nepalyp_travel_agents_category_extraction():
    """Test that nepalyp_travel_agents correctly extracts Travel_agents category."""
    scraper = get_scraper("nepalyp_travel_agents")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Travel_agents"


def test_nepalyp_tour_operators_registered_in_registry():
    """Test that nepalyp_tour_operators is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_tour_operators")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_tour_operators"


def test_nepalyp_tour_operators_category_extraction():
    """Test that nepalyp_tour_operators correctly extracts Tour_operators category."""
    scraper = get_scraper("nepalyp_tour_operators")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Tour_operators"


def test_nepalyp_shopping_centres_registered_in_registry():
    """Test that nepalyp_shopping_centres is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_shopping_centres")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_shopping_centres"


def test_nepalyp_shopping_centres_category_extraction():
    """Test that nepalyp_shopping_centres correctly extracts Shopping_centres category."""
    scraper = get_scraper("nepalyp_shopping_centres")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Shopping_centres"


def test_nepalyp_clinics_registered_in_registry():
    """Test that nepalyp_clinics is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_clinics")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_clinics"


def test_nepalyp_clinics_category_extraction():
    """Test that nepalyp_clinics correctly extracts Doctors_and_Clinics category."""
    scraper = get_scraper("nepalyp_clinics")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Doctors_and_Clinics"


def test_nepalyp_car_rental_registered_in_registry():
    """Test that nepalyp_car_rental is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_car_rental")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_car_rental"


def test_nepalyp_car_rental_category_extraction():
    """Test that nepalyp_car_rental correctly extracts Car_rental category."""
    scraper = get_scraper("nepalyp_car_rental")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Car_rental"


def test_nepalyp_bakers_registered_in_registry():
    """Test that nepalyp_bakers is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_bakers")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_bakers"


def test_nepalyp_bakers_category_extraction():
    """Test that nepalyp_bakers correctly extracts Bakers category."""
    scraper = get_scraper("nepalyp_bakers")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Bakers"


def test_nepalyp_insurance_registered_in_registry():
    """Test that nepalyp_insurance is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_insurance")

    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_insurance"


def test_nepalyp_insurance_category_extraction():
    """Test that nepalyp_insurance correctly extracts Insurance_companies category."""
    scraper = get_scraper("nepalyp_insurance")

    category = scraper._get_category_from_source_name()

    assert category == "Insurance_companies"


# Phase 7 - Priority 2: New category sources

def test_nepalyp_real_estate_registered_in_registry():
    """Test that nepalyp_real_estate is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_real_estate")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_real_estate"


def test_nepalyp_real_estate_category_extraction():
    """Test that nepalyp_real_estate correctly extracts Real_estate category."""
    scraper = get_scraper("nepalyp_real_estate")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Real_estate"


def test_nepalyp_petrol_stations_registered_in_registry():
    """Test that nepalyp_petrol_stations is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_petrol_stations")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_petrol_stations"


def test_nepalyp_petrol_stations_category_extraction():
    """Test that nepalyp_petrol_stations correctly extracts Petrol_stations category."""
    scraper = get_scraper("nepalyp_petrol_stations")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Petrol_stations"


def test_nepalyp_motorcycle_dealers_registered_in_registry():
    """Test that nepalyp_motorcycle_dealers is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_motorcycle_dealers")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_motorcycle_dealers"


def test_nepalyp_motorcycle_dealers_category_extraction():
    """Test that nepalyp_motorcycle_dealers correctly extracts Motor_cycle_dealers category."""
    scraper = get_scraper("nepalyp_motorcycle_dealers")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Motor_cycle_dealers"


def test_nepalyp_tourist_attractions_registered_in_registry():
    """Test that nepalyp_tourist_attractions is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_tourist_attractions")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_tourist_attractions"


def test_nepalyp_tourist_attractions_category_extraction():
    """Test that nepalyp_tourist_attractions correctly extracts Tourist_attractions category."""
    scraper = get_scraper("nepalyp_tourist_attractions")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Tourist_attractions"


def test_nepalyp_homestays_registered_in_registry():
    """Test that nepalyp_homestays is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_homestays")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_homestays"


def test_nepalyp_homestays_category_extraction():
    """Test that nepalyp_homestays correctly extracts Home_stays category."""
    scraper = get_scraper("nepalyp_homestays")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Home_stays"


def test_nepalyp_resorts_registered_in_registry():
    """Test that nepalyp_resorts is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_resorts")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_resorts"


def test_nepalyp_resorts_category_extraction():
    """Test that nepalyp_resorts correctly extracts Resorts category."""
    scraper = get_scraper("nepalyp_resorts")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Resorts"


def test_nepalyp_courier_registered_in_registry():
    """Test that nepalyp_courier is registered and resolves to NepalYPScraper."""
    scraper = get_scraper("nepalyp_courier")
    
    assert isinstance(scraper, NepalYPScraper)
    assert scraper.source_name == "nepalyp_courier"


def test_nepalyp_courier_category_extraction():
    """Test that nepalyp_courier correctly extracts Courier_services category."""
    scraper = get_scraper("nepalyp_courier")
    
    category = scraper._get_category_from_source_name()
    
    assert category == "Courier_services"
