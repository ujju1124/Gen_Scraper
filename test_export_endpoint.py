"""
Test script for Feature 4 - Export Endpoint
Tests CSV and JSON export functionality with filters
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def test_export_endpoint():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("=" * 80)
        print("FEATURE 4 - EXPORT ENDPOINT TEST")
        print("=" * 80)
        
        try:
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
            print("✅ Admin Panel loaded")
            
            # Step 3: Test CSV Export (no filters)
            print("\n[3/6] Testing CSV export (no filters)...")
            
            # Make API call directly
            response = await page.evaluate("""
                async () => {
                    const response = await fetch('http://localhost:8000/api/v1/admin/export?format=csv', {
                        credentials: 'include'
                    });
                    const text = await response.text();
                    return {
                        status: response.status,
                        contentType: response.headers.get('content-type'),
                        contentDisposition: response.headers.get('content-disposition'),
                        bodyPreview: text.substring(0, 200)
                    };
                }
            """)
            
            print(f"   Status: {response['status']}")
            print(f"   Content-Type: {response['contentType']}")
            print(f"   Content-Disposition: {response['contentDisposition']}")
            print(f"   Body preview: {response['bodyPreview']}")
            
            if response['status'] == 200 and 'text/csv' in response['contentType']:
                print("✅ CSV export successful")
            else:
                print(f"❌ CSV export failed: {response}")
            
            # Step 4: Test JSON Export (no filters)
            print("\n[4/6] Testing JSON export (no filters)...")
            
            response = await page.evaluate("""
                async () => {
                    const response = await fetch('http://localhost:8000/api/v1/admin/export?format=json', {
                        credentials: 'include'
                    });
                    const text = await response.text();
                    return {
                        status: response.status,
                        contentType: response.headers.get('content-type'),
                        contentDisposition: response.headers.get('content-disposition'),
                        body: text
                    };
                }
            """)
            
            print(f"   Status: {response['status']}")
            print(f"   Content-Type: {response['contentType']}")
            print(f"   Content-Disposition: {response['contentDisposition']}")
            
            if response['status'] == 200 and response['contentType'] == 'application/json':
                # Parse JSON to verify structure
                data = json.loads(response['body'])
                print(f"   Metadata: {data.get('metadata', {})}")
                print(f"   Results count: {len(data.get('results', []))}")
                print("✅ JSON export successful")
            else:
                print(f"❌ JSON export failed: {response}")
            
            # Step 5: Test CSV Export with filters
            print("\n[5/6] Testing CSV export with status filter (PENDING)...")
            
            response = await page.evaluate("""
                async () => {
                    const response = await fetch('http://localhost:8000/api/v1/admin/export?format=csv&status=PENDING', {
                        credentials: 'include'
                    });
                    return {
                        status: response.status,
                        contentType: response.headers.get('content-type')
                    };
                }
            """)
            
            print(f"   Status: {response['status']}")
            print(f"   Content-Type: {response['contentType']}")
            
            if response['status'] == 200:
                print("✅ CSV export with filter successful")
            else:
                print(f"❌ CSV export with filter failed")
            
            # Step 6: Test invalid format
            print("\n[6/6] Testing invalid format (should return 400)...")
            
            response = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('http://localhost:8000/api/v1/admin/export?format=xml', {
                            credentials: 'include'
                        });
                        const text = await response.text();
                        return {
                            status: response.status,
                            body: text
                        };
                    } catch (error) {
                        return {
                            status: 'error',
                            body: error.message
                        };
                    }
                }
            """)
            
            print(f"   Status: {response['status']}")
            
            if response['status'] == 400:
                print("✅ Invalid format correctly rejected")
            else:
                print(f"❌ Invalid format should return 400, got {response['status']}")
            
            print("\n" + "=" * 80)
            print("EXPORT ENDPOINT TEST COMPLETED")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ Error during test: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_export_endpoint())
