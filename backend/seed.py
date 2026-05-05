"""
Seed script for initial database data.
Inserts categories, city bounding boxes, placeholder source, Booking.com source, and admin user.
"""
import sys
import json
from passlib.context import CryptContext
from sqlalchemy import text
from database import SessionLocal, engine
from models import Category, CityBoundingBox, Source, User
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    # Validate required environment variables
    if not settings.ADMIN_PASSWORD:
        print("ERROR: ADMIN_PASSWORD environment variable is required but not set.")
        sys.exit(1)
    
    if not settings.ADMIN_EMAIL:
        print("ERROR: ADMIN_EMAIL environment variable is required but not set.")
        sys.exit(1)
    
    db = SessionLocal()
    
    try:
        print("Starting seed script...")
        
        # 1. Insert 30 categories
        print("Seeding categories...")
        categories_data = [
            ("hotels", "Hotels"),
            ("hostels", "Hostels"),
            ("guesthouses", "Guesthouses"),
            ("resorts", "Resorts"),
            ("lodges", "Lodges"),
            ("restaurants", "Restaurants"),
            ("cafes", "Cafes"),
            ("bakeries", "Bakeries"),
            ("pharmacies", "Pharmacies"),
            ("hospitals", "Hospitals"),
            ("clinics", "Clinics"),
            ("dental_clinics", "Dental Clinics"),
            ("banks", "Banks"),
            ("atms", "ATMs"),
            ("petrol_stations", "Petrol Stations"),
            ("supermarkets", "Supermarkets"),
            ("schools", "Schools"),
            ("colleges", "Colleges"),
            ("government_offices", "Government Offices"),
            ("police_stations", "Police Stations"),
            ("fire_stations", "Fire Stations"),
            ("embassies", "Embassies"),
            ("trekking_agencies", "Trekking Agencies"),
            ("travel_agencies", "Travel Agencies"),
            ("car_rentals", "Car Rentals"),
            ("bus_stations", "Bus Stations"),
            ("temples", "Temples"),
            ("museums", "Museums"),
            ("parks", "Parks"),
            ("gyms", "Gyms"),
        ]
        
        for name, display_name in categories_data:
            db.execute(
                text("""
                    INSERT INTO categories (name, display_name)
                    VALUES (:name, :display_name)
                    ON CONFLICT (name) DO NOTHING
                """),
                {"name": name, "display_name": display_name}
            )
        db.commit()
        print(f"✓ Seeded {len(categories_data)} categories")
        
        # 2. Insert 10 city bounding boxes
        print("Seeding city bounding boxes...")
        cities_data = [
            ("Kathmandu", 27.62, 85.18, 27.82, 85.45),
            ("Pokhara", 28.16, 83.92, 28.28, 84.06),
            ("Chitwan", 27.52, 84.28, 27.75, 84.55),
            ("Biratnagar", 26.40, 87.20, 26.55, 87.35),
            ("Birgunj", 26.94, 84.84, 27.05, 85.00),
            ("Butwal", 27.64, 83.38, 27.76, 83.52),
            ("Dharan", 26.76, 87.24, 26.85, 87.35),
            ("Hetauda", 27.39, 84.86, 27.48, 84.98),
            ("Lalitpur", 27.62, 85.28, 27.70, 85.36),
            ("Bhaktapur", 27.66, 85.38, 27.72, 85.45),
        ]
        
        for city_name, min_lat, min_lon, max_lat, max_lon in cities_data:
            db.execute(
                text("""
                    INSERT INTO city_bounding_boxes (city_name, min_lat, min_lon, max_lat, max_lon)
                    VALUES (:city_name, :min_lat, :min_lon, :max_lat, :max_lon)
                    ON CONFLICT (city_name) DO NOTHING
                """),
                {
                    "city_name": city_name,
                    "min_lat": min_lat,
                    "min_lon": min_lon,
                    "max_lat": max_lat,
                    "max_lon": max_lon
                }
            )
        db.commit()
        print(f"✓ Seeded {len(cities_data)} city bounding boxes")
        
        # 3. Insert Booking.com source with field_hints and AUTO heal mode
        print("Seeding Booking.com source...")
        booking_field_hints = {
            "name": "Hotel Himalaya",
            "address": "Sahid Sukra Marg, Kathmandu 44600, Nepal",
            "phone": "+977 1-5523900",
            "email": "info@hotelhimalaya.com",
            "website": "https://www.hotelhimalaya.com",
            "rating_overall": "8.5",
            "review_count": "1250",
            "price_min": "3500",
            "latitude": "27.7172",
            "longitude": "85.3240"
        }
        
        # Check if Booking.com source already exists
        existing_booking = db.execute(
            text("SELECT id FROM sources WHERE name = 'booking_com'")
        ).fetchone()
        
        if not existing_booking:
            db.execute(
                text("""
                    INSERT INTO sources (name, display_name, category_id, base_url, heal_mode, field_hints, is_active)
                    VALUES (:name, :display_name, :category_id, :base_url, :heal_mode, CAST(:field_hints AS jsonb), :is_active)
                """),
                {
                    "name": "booking_com",
                    "display_name": "Booking.com",
                    "category_id": 1,  # hotels category
                    "base_url": "https://www.booking.com",
                    "heal_mode": "AUTO",
                    "field_hints": json.dumps(booking_field_hints),
                    "is_active": True
                }
            )
            db.commit()
            print("✓ Seeded Booking.com source")
        else:
            print("✓ Booking.com source already exists")
        
        # 4b. Insert Phase 4B sources (Agoda, OYO Rooms, eSewa Hotels, NepalYP, Hostelworld) - INACTIVE until selectors provided
        print("Seeding Phase 4B sources (stubs)...")
        phase4b_sources = [
            ("agoda", "Agoda", "https://www.agoda.com", False),
            ("oyo_rooms", "OYO Rooms", "https://www.oyorooms.com", False),
            ("esewa_hotels", "eSewa Hotels", "https://esewahotels.com", False),
            ("nepalyp", "NepalYP", "https://www.nepalyp.com", False),
            ("hostelworld", "Hostelworld", "https://www.hostelworld.com", True),  # ACTIVE - selectors configured
            ("directoryofnepal_hotels", "DirectoryOfNepal Hotels", "https://www.directoryofnepal.com", True),  # ACTIVE - selectors confirmed
        ]
        
        for source_name, display_name, base_url, is_active in phase4b_sources:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, 
                                (SELECT id FROM categories WHERE name = 'hotels'), 
                                :is_active, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE - awaiting selectors"
                print(f"✓ Seeded {display_name} source ({status})")
            else:
                # Update is_active status if source exists
                db.execute(
                    text("""
                        UPDATE sources 
                        SET is_active = :is_active 
                        WHERE name = :name
                    """),
                    {"name": source_name, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ {display_name} source already exists (updated to {status})")
        
        # Phase 5 - Restaurant sources
        print("Seeding Phase 5 restaurant sources...")
        phase5_restaurant_sources = [
            # foodmandu: is_active=False — strong anti-bot (Cloudflare/Angular SPA)
            # Google Maps covers restaurant data adequately as universal source
            # Revisit if Foodmandu relaxes protection or proxies become available
            ("foodmandu", "Foodmandu", "https://foodmandu.com", False),
            ("nepalyp_restaurants", "NepalYP Restaurants", "https://www.nepalyp.com", False),
            ("directoryofnepal_restaurants", "DirectoryOfNepal Restaurants", "https://www.directoryofnepal.com", True),  # ACTIVE - same selectors as pharmacies
        ]
        
        for source_name, display_name, base_url, is_active in phase5_restaurant_sources:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, 
                                (SELECT id FROM categories WHERE name = 'restaurants'), 
                                :is_active, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE - awaiting selectors"
                print(f"✓ Seeded {display_name} source ({status})")
            else:
                # Update is_active status if source exists
                db.execute(
                    text("""
                        UPDATE sources 
                        SET is_active = :is_active 
                        WHERE name = :name
                    """),
                    {"name": source_name, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ {display_name} source already exists (updated to {status})")
        
        # Phase 5 - Pharmacy sources
        print("Seeding Phase 5 pharmacy sources (stubs)...")
        phase5_pharmacy_sources = [
            ("nepalyp_pharmacies", "NepalYP Pharmacies", "https://www.nepalyp.com", False),
            ("nepalyp_drugstores", "NepalYP Drugstores", "https://www.nepalyp.com", False),
            ("directoryofnepal_pharmacies", "DirectoryOfNepal Pharmacies", "https://www.directoryofnepal.com", True),  # ACTIVE - selectors confirmed
        ]
        
        for source_name, display_name, base_url, is_active in phase5_pharmacy_sources:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, 
                                (SELECT id FROM categories WHERE name = 'pharmacies'), 
                                :is_active, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE - awaiting selectors"
                print(f"✓ Seeded {display_name} source ({status})")
            else:
                # Update is_active status if source exists
                db.execute(
                    text("""
                        UPDATE sources 
                        SET is_active = :is_active 
                        WHERE name = :name
                    """),
                    {"name": source_name, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ {display_name} source already exists (updated to {status})")
        
        # Phase 5 - Hospital sources
        print("Seeding Phase 5 hospital sources...")
        phase5_hospital_sources = [
            ("nepalyp_hospitals", "NepalYP Hospitals", "https://www.nepalyp.com"),
        ]
        
        for source_name, display_name, base_url in phase5_hospital_sources:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, 
                                (SELECT id FROM categories WHERE name = 'hospitals'), 
                                FALSE, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url}
                )
                print(f"✓ Seeded {display_name} source (INACTIVE - awaiting selectors)")
            else:
                print(f"✓ {display_name} source already exists")
        
        # Phase 5 - Additional NepalYP category sources
        print("Seeding additional NepalYP category sources...")
        nepalyp_category_sources = [
            ("nepalyp_banks", "NepalYP Banks", "https://www.nepalyp.com/category/Bankscredit_unions/city:{location}", "banks", True),
            ("nepalyp_schools", "NepalYP Schools", "https://www.nepalyp.com/category/Schools/city:{location}", "schools", True),
            ("nepalyp_colleges", "NepalYP Colleges", "https://www.nepalyp.com/category/Colleges/city:{location}", "colleges", True),
            ("nepalyp_travel_agents", "NepalYP Travel Agents", "https://www.nepalyp.com/category/Travel_agents/city:{location}", "travel_agencies", True),
            ("nepalyp_tour_operators", "NepalYP Tour Operators", "https://www.nepalyp.com/category/Tour_operators/city:{location}", "trekking_agencies", True),
            ("nepalyp_shopping_centres", "NepalYP Shopping Centres", "https://www.nepalyp.com/category/Shopping_centres/city:{location}", "supermarkets", True),
            ("nepalyp_clinics", "NepalYP Doctors & Clinics", "https://www.nepalyp.com/category/Doctors_and_Clinics/city:{location}", "clinics", True),
            ("nepalyp_car_rental", "NepalYP Car Rental", "https://www.nepalyp.com/category/Car_rental/city:{location}", "car_rentals", True),
            ("nepalyp_bakers", "NepalYP Bakeries", "https://www.nepalyp.com/category/Bakers/city:{location}", "bakeries", True),
            ("nepalyp_insurance", "NepalYP Insurance Companies", "https://www.nepalyp.com/category/Insurance_companies/city:{location}", "banks", True),  # Using banks category as closest match
            ("nepalyp_real_estate", "NepalYP Real Estate", "https://www.nepalyp.com/category/Real_estate/city:{location}", "real_estate", True),
            ("nepalyp_petrol_stations", "NepalYP Petrol Stations", "https://www.nepalyp.com/category/Petrol_stations/city:{location}", "petrol_stations", True),
            ("nepalyp_motorcycle_dealers", "NepalYP Motorcycle Dealers", "https://www.nepalyp.com/category/Motor_cycle_dealers/city:{location}", "automotive", True),
            ("nepalyp_tourist_attractions", "NepalYP Tourist Attractions", "https://www.nepalyp.com/category/Tourist_attractions/city:{location}", "tourist_places", True),
            ("nepalyp_homestays", "NepalYP Homestays", "https://www.nepalyp.com/category/Home_stays/city:{location}", "homestays", True),
            ("nepalyp_resorts", "NepalYP Resorts", "https://www.nepalyp.com/category/Resorts/city:{location}", "resorts", True),
            ("nepalyp_courier", "NepalYP Courier & Moving", "https://www.nepalyp.com/category/Courier_services/city:{location}", "courier_moving", True),
        ]
        
        for source_name, display_name, base_url, category_name, is_active in nepalyp_category_sources:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, 
                                (SELECT id FROM categories WHERE name = :category_name), 
                                :is_active, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url, "category_name": category_name, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ Seeded {display_name} source ({status})")
            else:
                # Update is_active status if source exists
                db.execute(
                    text("""
                        UPDATE sources 
                        SET is_active = :is_active, base_url = :base_url
                        WHERE name = :name
                    """),
                    {"name": source_name, "is_active": is_active, "base_url": base_url}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ {display_name} source already exists (updated to {status})")
        
        db.commit()
        print("✓ Seeded Phase 4B and Phase 5 sources")
        
        # Phase 6 - Google Maps universal source
        print("Seeding Google Maps universal source...")
        google_maps_source = [
            ("google_maps", "Google Maps", "https://www.google.com/maps/search/{category}+in+{location}", None, True),  # category_id=None for universal support, ACTIVATED for live testing
        ]
        
        for source_name, display_name, base_url, category_id, is_active in google_maps_source:
            existing_source = db.execute(
                text("SELECT id FROM sources WHERE name = :name"),
                {"name": source_name}
            ).fetchone()
            
            if not existing_source:
                db.execute(
                    text("""
                        INSERT INTO sources (name, display_name, base_url, category_id, is_active, heal_mode)
                        VALUES (:name, :display_name, :base_url, :category_id, :is_active, 'MANUAL')
                    """),
                    {"name": source_name, "display_name": display_name, "base_url": base_url, "category_id": category_id, "is_active": is_active}
                )
                status = "ACTIVE" if is_active else "INACTIVE - awaiting live test"
                print(f"✓ Seeded {display_name} source ({status})")
            else:
                # Update is_active status if source exists
                db.execute(
                    text("""
                        UPDATE sources 
                        SET is_active = :is_active, base_url = :base_url, category_id = :category_id
                        WHERE name = :name
                    """),
                    {"name": source_name, "is_active": is_active, "base_url": base_url, "category_id": category_id}
                )
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"✓ {display_name} source already exists (updated to {status})")
        
        db.commit()
        
        # 5. Insert Booking.com selectors
        print("Seeding Booking.com selectors...")
        
        # Get booking_com source_id
        booking_source = db.execute(
            text("SELECT id FROM sources WHERE name = 'booking_com'")
        ).fetchone()
        
        if booking_source:
            booking_source_id = booking_source[0]
            
            # Define selectors (all are data-testid type)
            selectors_data = [
                ("name", "[data-testid='title']", "testid"),
                ("rating_overall", "[data-testid='review-score']", "testid"),
                ("price_min", "[data-testid='price-and-discounted-price']", "testid"),
                ("address", "[data-testid='address-link']", "testid"),
                ("thumbnail_url", "[data-testid='image']", "testid"),
                ("star_rating", "[data-testid='rating-stars']", "testid"),
                ("review_count", "[data-testid='review-score']", "testid"),
                ("source_url", "[data-testid='title-link']", "testid"),
            ]
            
            for field_name, selector, selector_type in selectors_data:
                db.execute(
                    text("""
                        INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
                        VALUES (:source_id, :field_name, :selector, :selector_type, :is_active)
                        ON CONFLICT (source_id, field_name) DO UPDATE
                        SET selector = EXCLUDED.selector,
                            selector_type = EXCLUDED.selector_type,
                            is_active = EXCLUDED.is_active
                    """),
                    {
                        "source_id": booking_source_id,
                        "field_name": field_name,
                        "selector": selector,
                        "selector_type": selector_type,
                        "is_active": True
                    }
                )
            
            db.commit()
            print(f"✓ Seeded {len(selectors_data)} selectors for Booking.com")
        else:
            print("⚠ Booking.com source not found, skipping selector seeding")
        
        # 5b. Insert Google Maps selectors
        print("Seeding Google Maps selectors...")
        
        # Get google_maps source_id
        google_maps_source = db.execute(
            text("SELECT id FROM sources WHERE name = 'google_maps'")
        ).fetchone()
        
        if google_maps_source:
            google_maps_source_id = google_maps_source[0]
            
            # Define selectors for Google Maps
            google_maps_selectors = [
                ("result_feed", "[role='feed']", "css"),
                ("result_card", "a.hfpxzc", "css"),
                ("name", "h1.DUwDvf, h1.fontHeadlineLarge", "css"),
                ("address", "[data-item-id='address'] .Io6YTe", "css"),
                ("phone", "[data-item-id*='phone:tel'] .Io6YTe", "css"),
                ("rating", "div.F7nice span[aria-hidden='true']", "css"),
                ("review_count", "div.F7nice span[aria-label*='reviews']", "css"),
                ("website", "a[data-item-id='authority']", "css"),
                ("category_label", "button.DkEaL", "css"),
                ("business_status", "span.ZDu9vd span", "css"),
            ]
            
            for field_name, selector, selector_type in google_maps_selectors:
                db.execute(
                    text("""
                        INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
                        VALUES (:source_id, :field_name, :selector, :selector_type, :is_active)
                        ON CONFLICT (source_id, field_name) DO UPDATE
                        SET selector = EXCLUDED.selector,
                            selector_type = EXCLUDED.selector_type,
                            is_active = EXCLUDED.is_active
                    """),
                    {
                        "source_id": google_maps_source_id,
                        "field_name": field_name,
                        "selector": selector,
                        "selector_type": selector_type,
                        "is_active": True
                    }
                )
            
            db.commit()
            print(f"✓ Seeded {len(google_maps_selectors)} selectors for Google Maps")
        else:
            print("⚠ Google Maps source not found, skipping selector seeding")
        
        # 6. Insert admin user
        print("Seeding admin user...")
        password_hash = pwd_context.hash(settings.ADMIN_PASSWORD)
        db.execute(
            text("""
                INSERT INTO users (email, password_hash, role)
                VALUES (:email, :password_hash, 'admin')
                ON CONFLICT (email) DO NOTHING
            """),
            {"email": settings.ADMIN_EMAIL, "password_hash": password_hash}
        )
        db.commit()
        print(f"✓ Seeded admin user: {settings.ADMIN_EMAIL}")
        
        print("\n✅ Seed script completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Seed script failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

