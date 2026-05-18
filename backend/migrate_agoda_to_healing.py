"""
Migration script to add Agoda to the healing system.

This script:
1. Adds selectors to scraper_selectors table
2. Adds field hints to sources table
3. Sets heal_mode to AUTO
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.scraper_selector import ScraperSelector
from models.source import Source

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scraper:scraper_pass@localhost:5433/scraper_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def migrate():
    db = SessionLocal()
    
    try:
        # Get Agoda source
        agoda = db.query(Source).filter(Source.name == "agoda").first()
        if not agoda:
            print("❌ Agoda source not found")
            return
        
        print(f"✅ Found Agoda source (ID: {agoda.id})")
        
        # Add selectors
        selectors = [
            {
                "field_name": "name",
                "selector": "h3, [data-element-name='property-name'], [class*='PropertyName']",
                "selector_type": "css",
                "description": "Hotel name - tries h3, data attribute, or class name"
            },
            {
                "field_name": "address",
                "selector": "[class*='address'], [class*='location'], p",
                "selector_type": "css",
                "description": "Hotel address or location"
            },
            {
                "field_name": "price",
                "selector": "[class*='Price'], [class*='price']",
                "selector_type": "css",
                "description": "Price element"
            },
            {
                "field_name": "rating",
                "selector": "[class*='Review'], [class*='rating'], [class*='Rating']",
                "selector_type": "css",
                "description": "Rating element"
            },
        ]
        
        for sel_data in selectors:
            # Check if selector already exists
            existing = db.query(ScraperSelector).filter(
                ScraperSelector.source_id == agoda.id,
                ScraperSelector.field_name == sel_data["field_name"]
            ).first()
            
            if existing:
                print(f"⚠️  Selector for '{sel_data['field_name']}' already exists, skipping")
                continue
            
            selector = ScraperSelector(
                source_id=agoda.id,
                field_name=sel_data["field_name"],
                selector=sel_data["selector"],
                selector_type=sel_data["selector_type"],
                is_active=True,
                verified_at=datetime.utcnow()
            )
            db.add(selector)
            print(f"✅ Added selector for '{sel_data['field_name']}'")
        
        # Add field hints (real example values from Agoda)
        field_hints = {
            "name": "Hotel Shanker",
            "address": "Lazimpat, Kathmandu",
            "price": "NPR 5,000",
            "rating": "8.5"
        }
        
        agoda.field_hints = field_hints
        print(f"✅ Added field hints")
        
        # Set heal_mode to AUTO
        agoda.heal_mode = "AUTO"
        print(f"✅ Set heal_mode to AUTO")
        
        # Commit changes
        db.commit()
        print("\n🎉 Migration complete!")
        print(f"   - Added {len(selectors)} selectors")
        print(f"   - Added {len(field_hints)} field hints")
        print(f"   - Set heal_mode to AUTO")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
