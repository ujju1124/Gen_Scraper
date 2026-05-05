#!/usr/bin/env python3
"""
Quick test script to verify if sources return actual data
"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from scrapers.booking_com import BookingComScraper
from scrapers.directoryofnepal import DirectoryOfNepalScraper
from scrapers.nepalyp import NepalYPScraper

async def test_source(scraper_class, source_name, location="Kathmandu"):
    """Test a single source"""
    print(f"\n{'='*60}")
    print(f"Testing: {source_name}")
    print(f"Location: {location}")
    print(f"{'='*60}")
    
    try:
        scraper = scraper_class()
        results = await scraper.scrape(location=location, max_results=5)
        
        print(f"✅ SUCCESS: Got {len(results)} results")
        
        if results:
            print(f"\nSample result:")
            sample = results[0]
            print(f"  Name: {sample.get('name', 'N/A')}")
            print(f"  Address: {sample.get('address', 'N/A')}")
            print(f"  Phone: {sample.get('phone_primary', 'N/A')}")
            print(f"  Website: {sample.get('website', 'N/A')}")
        else:
            print("⚠️  WARNING: No results returned")
            
        return True, len(results)
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False, 0

async def main():
    """Test multiple sources"""
    print("\n" + "="*60)
    print("SOURCE VERIFICATION TEST")
    print("="*60)
    
    sources_to_test = [
        (BookingComScraper, "Booking.com"),
        (DirectoryOfNepalScraper, "DirectoryOfNepal Hotels"),
        (NepalYPScraper, "NepalYP Hotels"),
    ]
    
    results = []
    for scraper_class, name in sources_to_test:
        success, count = await test_source(scraper_class, name)
        results.append((name, success, count))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for name, success, count in results:
        status = "✅ PASS" if success and count > 0 else "❌ FAIL"
        print(f"{status} - {name}: {count} results")
    
    total_success = sum(1 for _, success, count in results if success and count > 0)
    print(f"\nTotal: {total_success}/{len(results)} sources working")

if __name__ == "__main__":
    asyncio.run(main())
