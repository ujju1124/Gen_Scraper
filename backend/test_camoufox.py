import asyncio
from camoufox.async_api import AsyncCamoufox

async def test():
    print("Starting AsyncCamoufox...")
    async with AsyncCamoufox(headless=True, os="windows", geoip=False) as browser:
        print("Browser started!")
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        print("Context created!")
        page = await context.new_page()
        print("Page created!")
        await page.goto("https://www.google.com", timeout=10000)
        print(f"Navigated to: {page.url}")
        title = await page.title()
        print(f"Page title: {title}")
        await page.close()
        await context.close()
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test())
