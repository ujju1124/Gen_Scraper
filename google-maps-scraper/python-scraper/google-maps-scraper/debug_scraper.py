#!/usr/bin/env python3
"""
Debug script to test Google Maps scraping and see what elements are available
"""

import undetected_chromedriver as uc
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_google_maps_search(search_query="restaurants in New York"):
    """Debug function to test Google Maps search"""
    
    print(f"🔍 Testing search query: '{search_query}'")
    
    # Setup Chrome options
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Disable images to speed up loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        print("🚀 Starting Chrome browser...")
        driver = uc.Chrome(options=options)
        driver.maximize_window()
        driver.implicitly_wait(10)
        
        # Format search query for URL
        query_with_plus = "+".join(search_query.split())
        url = f"https://www.google.com/maps/search/{query_with_plus}/"
        
        print(f"🌐 Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        sleep(5)
        
        # Check page title
        print(f"📄 Page title: {driver.title}")
        
        # Try to find the feed element (results container)
        print("🔍 Looking for results feed element...")
        feed_element = driver.execute_script(
            """return document.querySelector("[role='feed']")"""
        )
        
        if feed_element:
            print("✅ Found feed element!")
            
            # Get all result links
            result_links = driver.execute_script("""
                const feed = document.querySelector("[role='feed']");
                if (feed) {
                    const links = feed.querySelectorAll('a.hfpxzc');
                    return Array.from(links).map(link => link.href);
                }
                return [];
            """)
            
            print(f"📊 Found {len(result_links)} result links")
            
            if result_links:
                print("🎯 First few results:")
                for i, link in enumerate(result_links[:3]):
                    print(f"  {i+1}. {link}")
            
        else:
            print("❌ No feed element found!")
            
            # Try alternative selectors
            print("🔍 Trying alternative selectors...")
            
            # Check for search results container
            alternatives = [
                "[data-value='Search results']",
                ".m6QErb",
                "[role='main']",
                ".Nv2PK",
                ".bJzME"
            ]
            
            for selector in alternatives:
                element = driver.execute_script(f"return document.querySelector('{selector}')")
                if element:
                    print(f"✅ Found element with selector: {selector}")
                else:
                    print(f"❌ No element found with selector: {selector}")
            
            # Get page source snippet to analyze
            print("📝 Page source analysis:")
            page_source = driver.page_source
            
            # Look for common Google Maps elements
            if "maps" in page_source.lower():
                print("✅ Page contains 'maps' text")
            if "search" in page_source.lower():
                print("✅ Page contains 'search' text")
            if "results" in page_source.lower():
                print("✅ Page contains 'results' text")
                
            # Check for potential error messages
            if "no results" in page_source.lower():
                print("⚠️  Page contains 'no results' text")
            if "try again" in page_source.lower():
                print("⚠️  Page contains 'try again' text")
                
        # Take a screenshot for debugging
        print("📸 Taking screenshot...")
        driver.save_screenshot("debug_screenshot.png")
        print("💾 Screenshot saved as 'debug_screenshot.png'")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        
    finally:
        if driver:
            print("🔚 Closing browser...")
            driver.quit()

if __name__ == "__main__":
    # Test with a simple search query
    debug_google_maps_search("pizza near me")