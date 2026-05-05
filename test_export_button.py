"""
Test script for Feature 4 - Export Button (Frontend)
Tests the export button UI and download functionality
"""
import asyncio
from playwright.async_api import async_playwright

async def test_export_button():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("=" * 80)
        print("FEATURE 4 - EXPORT BUTTON TEST (FRONTEND)")
        print("=" * 80)
        
        try:
            # Capture console messages
            console_messages = []
            page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
            page.on("pageerror", lambda exc: console_messages.append(f"ERROR: {exc}"))
            
            # Step 1: Login as admin
            print("\n[1/6] Logging in as admin...")
            await page.goto("http://localhost:5173/login")
            await page.wait_for_load_state("networkidle")
            
            await page.fill('input[type="email"]', "admin@example.com")
            await page.fill('input[type="password"]', "admin123")
            await page.click('button[type="submit"]')
            
            await page.wait_for_url("**/dashboard", timeout=10000)
            print("✅ Login successful")
            
            # Step 2: Navigate to Admin Panel
            print("\n[2/6] Navigating to Admin Panel...")
            await page.goto("http://localhost:5173/admin")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Print console messages
            if console_messages:
                print("\n   Console messages:")
                for msg in console_messages[-10:]:  # Last 10 messages
                    print(f"     {msg}")
            
            print("✅ Admin Panel loaded")
            
            # Step 3: Check if Export button exists
            print("\n[3/6] Checking if Export button exists...")
            
            # Take a screenshot for debugging
            await page.screenshot(path="admin_page_debug.png")
            print("   Screenshot saved: admin_page_debug.png")
            
            # Try to find the button with different selectors
            export_button = await page.query_selector('button:has-text("Export")')
            
            if not export_button:
                # Try alternative selector
                export_button = await page.query_selector('[aria-label="Export results"]')
            
            if export_button:
                print("✅ Export button found")
            else:
                print("❌ Export button not found")
                # Print page content for debugging
                content = await page.content()
                if "Export" in content:
                    print("   'Export' text found in page, but button not accessible")
                return
            
            # Step 4: Check if button is enabled (should be enabled if there are results)
            print("\n[4/6] Checking if Export button is enabled...")
            is_disabled = await export_button.is_disabled()
            
            if not is_disabled:
                print("✅ Export button is enabled")
            else:
                print("⚠️  Export button is disabled (no results)")
            
            # Step 5: Click Export button to open dropdown
            print("\n[5/6] Clicking Export button to open dropdown...")
            await export_button.click()
            await asyncio.sleep(1)
            
            # Check if dropdown appeared
            csv_option = await page.query_selector('button:has-text("Export as CSV")')
            json_option = await page.query_selector('button:has-text("Export as JSON")')
            
            if csv_option and json_option:
                print("✅ Export dropdown opened with CSV and JSON options")
            else:
                print("❌ Export dropdown did not open correctly")
                return
            
            # Step 6: Test CSV export
            print("\n[6/6] Testing CSV export...")
            
            # Set up download listener
            async with page.expect_download() as download_info:
                await csv_option.click()
            
            download = await download_info.value
            filename = download.suggested_filename
            
            print(f"   Downloaded file: {filename}")
            
            if filename.endswith('.csv'):
                print("✅ CSV export successful")
            else:
                print(f"❌ Expected CSV file, got: {filename}")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Test JSON export
            print("\n[BONUS] Testing JSON export...")
            await export_button.click()
            await asyncio.sleep(1)
            
            json_option = await page.query_selector('button:has-text("Export as JSON")')
            
            async with page.expect_download() as download_info2:
                await json_option.click()
            
            download2 = await download_info2.value
            filename2 = download2.suggested_filename
            
            print(f"   Downloaded file: {filename2}")
            
            if filename2.endswith('.json'):
                print("✅ JSON export successful")
            else:
                print(f"❌ Expected JSON file, got: {filename2}")
            
            print("\n" + "=" * 80)
            print("EXPORT BUTTON TEST COMPLETED")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ Error during test: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_export_button())
