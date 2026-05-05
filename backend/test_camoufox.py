"""
Camoufox Standalone Test Script

This script tests that Camoufox browser works correctly and can access
Booking.com without being blocked by anti-bot measures.

Run with: python backend/test_camoufox.py
"""

import sys
from camoufox.sync_api import Camoufox


def main():
    """
    Test Camoufox browser integration.
    
    Steps:
    1. Launch Camoufox with headless=True, os="windows", geoip=True
    2. Navigate to https://www.booking.com
    3. Check page loaded (title contains "Booking")
    4. Check not blocked (no CAPTCHA detected)
    5. Print success message
    6. Close browser cleanly
    """
    
    try:
        print("🚀 Launching Camoufox browser...")
        
        # Step 1: Launch Camoufox and get page
        with Camoufox(
            headless=True,
            os="windows"
        ) as browser:
            page = browser.new_context().new_page()
            
            print("✓ Camoufox browser launched successfully")
        
            # Step 2: Navigate to Booking.com
            print("🌐 Navigating to https://www.booking.com...")
            page.goto("https://www.booking.com", wait_until="domcontentloaded", timeout=30000)
            
            print("✓ Page loaded")
            
            # Step 3: Check page title
            title = page.title()
            print(f"📄 Page title: {title}")
            
            if "booking" not in title.lower():
                print(f"❌ FAILED: Page title does not contain 'Booking'")
                print(f"   Expected: Title containing 'Booking'")
                print(f"   Got: {title}")
                sys.exit(1)
            
            print("✓ Page title contains 'Booking'")
            
            # Step 4: Check for CAPTCHA
            print("🔍 Checking for CAPTCHA...")
            
            # Check title for CAPTCHA keywords
            if any(keyword in title.lower() for keyword in ['captcha', 'robot', 'verify', 'challenge']):
                print(f"❌ FAILED: CAPTCHA detected in page title")
                print(f"   Title: {title}")
                sys.exit(1)
            
            # Check for CAPTCHA iframes
            iframes = page.query_selector_all('iframe')
            for iframe in iframes:
                src = iframe.get_attribute('src')
                if src and any(keyword in src.lower() for keyword in ['captcha', 'recaptcha', 'hcaptcha']):
                    print(f"❌ FAILED: CAPTCHA detected in iframe")
                    print(f"   Iframe src: {src}")
                    sys.exit(1)
            
            # Check HTML content for CAPTCHA
            html = page.content()
            if any(keyword in html.lower() for keyword in ['id="captcha"', 'class="captcha"', 'recaptcha', 'hcaptcha']):
                print(f"❌ FAILED: CAPTCHA detected in page HTML")
                sys.exit(1)
            
            print("✓ No CAPTCHA detected")
            
            # Step 5: Success!
            print("\n" + "="*60)
            print("✅ SUCCESS: Camoufox works, Booking.com not blocked")
            print("="*60)
            
            print("\n🔒 Browser will close cleanly")
        
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
        # Step 2: Navigate to Booking.com
        print("🌐 Navigating to https://www.booking.com...")
        page.goto("https://www.booking.com", wait_until="domcontentloaded", timeout=30000)
        
        print("✓ Page loaded")
        
        # Step 3: Check page title
        title = page.title()
        print(f"📄 Page title: {title}")
        
        if "booking" not in title.lower():
            print(f"❌ FAILED: Page title does not contain 'Booking'")
            print(f"   Expected: Title containing 'Booking'")
            print(f"   Got: {title}")
            sys.exit(1)
        
        print("✓ Page title contains 'Booking'")
        
        # Step 4: Check for CAPTCHA
        print("🔍 Checking for CAPTCHA...")
        
        # Check title for CAPTCHA keywords
        if any(keyword in title.lower() for keyword in ['captcha', 'robot', 'verify', 'challenge']):
            print(f"❌ FAILED: CAPTCHA detected in page title")
            print(f"   Title: {title}")
            sys.exit(1)
        
        # Check for CAPTCHA iframes
        iframes = page.query_selector_all('iframe')
        for iframe in iframes:
            src = iframe.get_attribute('src')
            if src and any(keyword in src.lower() for keyword in ['captcha', 'recaptcha', 'hcaptcha']):
                print(f"❌ FAILED: CAPTCHA detected in iframe")
                print(f"   Iframe src: {src}")
                sys.exit(1)
        
        # Check HTML content for CAPTCHA
        html = page.content()
        if any(keyword in html.lower() for keyword in ['id="captcha"', 'class="captcha"', 'recaptcha', 'hcaptcha']):
            print(f"❌ FAILED: CAPTCHA detected in page HTML")
            sys.exit(1)
        
        print("✓ No CAPTCHA detected")
        
        # Step 5: Success!
        print("\n" + "="*60)
        print("✅ SUCCESS: Camoufox works, Booking.com not blocked")
        print("="*60)


if __name__ == "__main__":
    main()
