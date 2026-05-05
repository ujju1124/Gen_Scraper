"""
Quick test script for new scrapers.

Tests instantiation and registry lookup. Full scrape tests require
a running DB + browser, so those are done via the frontend job trigger.

Run with: docker-compose exec backend python test_new_scrapers.py
"""
import sys
sys.path.insert(0, '/app')

from scrapers.agoda import AgodaScraper
from scrapers.oyo_rooms import OYORoomsScraper
from scrapers.esewa_hotels import ESewaHotelsScraper
from scrapers.nepalyp import NepalYPScraper
from scrapers.registry import get_scraper, list_scrapers
from scrapers.base_scraper import BaseScraper
import inspect


def test_scraper(scraper_class, name):
    """Test a single scraper for correct structure."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    try:
        scraper = scraper_class()
        print(f"  ✓ Instantiated: {scraper.__class__.__name__}")
        print(f"  ✓ source_name: {scraper.source_name}")

        # Verify it's a BaseScraper subclass
        assert isinstance(scraper, BaseScraper), "Not a BaseScraper subclass!"
        print(f"  ✓ Is BaseScraper subclass")

        # Verify _scrape is implemented (not abstract)
        assert not getattr(scraper._scrape, '__isabstractmethod__', False), \
            "_scrape is still abstract!"
        sig = inspect.signature(scraper._scrape)
        params = list(sig.parameters.keys())
        assert params == ['page', 'source', 'db', 'location'], \
            f"Wrong _scrape signature: {params}"
        print(f"  ✓ _scrape signature correct: {params}")

        # Verify run() is inherited from BaseScraper
        assert hasattr(scraper, 'run'), "Missing run() method!"
        print(f"  ✓ run() method present")

        return True

    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_registry():
    """Test that all new scrapers are in the registry."""
    print(f"\n{'='*60}")
    print("Testing Registry")
    print(f"{'='*60}")

    expected = ["booking_com", "agoda", "oyo_rooms", "esewa_hotels", "nepalyp"]
    available = list_scrapers()
    print(f"  Registered scrapers: {available}")

    all_ok = True
    for name in expected:
        if name in available:
            scraper = get_scraper(name)
            print(f"  ✓ {name} -> {scraper.__class__.__name__}")
        else:
            print(f"  ❌ {name} NOT in registry!")
            all_ok = False

    return all_ok


def main():
    print("\n" + "="*60)
    print("PHASE 4B SCRAPER STRUCTURE TESTS")
    print("="*60)

    scrapers = [
        (AgodaScraper, "Agoda"),
        (OYORoomsScraper, "OYO Rooms"),
        (ESewaHotelsScraper, "eSewa Hotels"),
        (NepalYPScraper, "NepalYP"),
    ]

    results = {}
    for scraper_class, name in scrapers:
        results[name] = test_scraper(scraper_class, name)

    results["Registry"] = test_registry()

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")

    total = len(results)
    passed = sum(1 for s in results.values() if s)
    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All structure tests passed! Ready for live scrape testing via frontend.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
