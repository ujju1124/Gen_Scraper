# Phase 4B Anti-Blocking Implementation Guide

**Critical Document**: Read Before Implementing TripAdvisor or eSewa Scrapers  
**Created**: April 29, 2026  
**Author**: Kiro AI Assistant

---

## ⚠️ CRITICAL WARNING

**TripAdvisor** and **eSewa** are known to block automated requests. Implementing these scrapers without proper anti-blocking measures will result in immediate failure.

This guide provides battle-tested strategies to bypass bot detection.

---

## Blocking Risk Assessment

| Scraper | Risk Level | Blocking Type | Mitigation Complexity |
|---------|------------|---------------|----------------------|
| Agoda | Medium | Rate limiting, basic detection | Medium |
| **TripAdvisor** | **HIGH** | **Aggressive bot detection, CAPTCHA** | **High** |
| **eSewa** | **Medium-High** | **Rate limiting, IP blocking** | **Medium** |
| NepalYP | Low | None expected | Low |

---

## Part 1: TripAdvisor Anti-Blocking Strategy

### Why TripAdvisor Blocks

1. **Commercial Protection**: Prevent data scraping for competitive analysis
2. **Server Load**: Reduce automated traffic
3. **User Experience**: Prioritize human users
4. **Legal Compliance**: Terms of Service enforcement

### Detection Methods Used

- **Fingerprinting**: Browser characteristics, WebGL, Canvas
- **Behavioral Analysis**: Mouse movements, timing patterns
- **Rate Limiting**: Requests per IP per time window
- **CAPTCHA**: PerimeterX, reCAPTCHA
- **IP Reputation**: Known datacenter IPs blocked

### Mitigation Strategy

#### 1. Use Camoufox with Full Stealth

```python
from camoufox import AsyncCamoufox

async def get_stealth_browser():
    """Get Camoufox browser with maximum stealth."""
    return await AsyncCamoufox(
        headless=False,  # Headless mode is easier to detect
        humanize=True,   # Enable human behavior simulation
        geoip=True,      # Use realistic geolocation
        exclude_addons=["webdriver"],  # Remove webdriver flag
        os="windows",    # Mimic Windows OS
        screen={
            "width": 1920,
            "height": 1080
        }
    )
```

#### 2. Randomize Everything

```python
import random

# Viewport sizes (common resolutions)
VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900}
]

# User agents (rotate)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
    # Add more
]

# Random delays (seconds)
DELAYS = {
    "page_load": (3, 6),
    "between_clicks": (1, 3),
    "scrolling": (0.5, 1.5),
    "reading": (2, 5)
}
```

#### 3. Simulate Human Behavior

```python
async def simulate_realistic_browsing(page):
    """Simulate how a real human browses."""
    
    # 1. Initial page scan (mouse movements)
    for _ in range(random.randint(3, 6)):
        x = random.randint(100, 1200)
        y = random.randint(100, 800)
        
        # Move mouse in curved path (more realistic)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    # 2. Read content (scroll down slowly)
    scroll_positions = [100, 250, 400, 600, 800]
    for position in scroll_positions:
        await page.evaluate(f"window.scrollTo(0, {position})")
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # 3. Hover over elements (simulate interest)
    hotel_cards = await page.query_selector_all('.hotel-card')
    if hotel_cards:
        for card in random.sample(hotel_cards, min(3, len(hotel_cards))):
            box = await card.bounding_box()
            if box:
                await page.mouse.move(
                    box['x'] + box['width'] / 2,
                    box['y'] + box['height'] / 2
                )
                await asyncio.sleep(random.uniform(0.5, 1.0))
    
    # 4. Random pause (reading time)
    await asyncio.sleep(random.uniform(2, 5))
```

#### 4. Detect Blocking Immediately

```python
async def is_tripadvisor_blocked(page) -> bool:
    """Detect if TripAdvisor is blocking us."""
    
    # Get page content
    content = await page.content()
    url = page.url
    
    # Check URL redirects
    if "denied" in url.lower() or "captcha" in url.lower():
        return True
    
    # Check for blocking text
    blocking_phrases = [
        "access denied",
        "unusual traffic",
        "verify you are a human",
        "please complete the security check",
        "automated requests",
        "robot"
    ]
    
    content_lower = content.lower()
    for phrase in blocking_phrases:
        if phrase in content_lower:
            logger.error(f"TripAdvisor blocking detected: '{phrase}'")
            return True
    
    # Check for CAPTCHA elements
    captcha_selectors = [
        "#px-captcha",
        ".g-recaptcha",
        "[data-callback='onCaptchaSuccess']",
        "iframe[src*='recaptcha']",
        "iframe[src*='perimeterx']"
    ]
    
    for selector in captcha_selectors:
        if await page.query_selector(selector):
            logger.error(f"CAPTCHA detected: {selector}")
            return True
    
    # Check for suspiciously small page
    if len(content) < 5000:
        logger.warning("Suspiciously small page - possible blocking")
        return True
    
    # Check for expected content
    hotel_cards = await page.query_selector_all('.hotel-card, [data-test="hotel-card"]')
    if not hotel_cards:
        logger.warning("No hotel cards found - possible blocking")
        return True
    
    return False
```

#### 5. Handle Blocking Gracefully

```python
async def handle_tripadvisor_blocking(page, attempt: int):
    """Handle blocking with appropriate response."""
    
    # Take screenshot for debugging
    screenshot_path = f"blocking_tripadvisor_{int(time.time())}.png"
    await page.screenshot(path=screenshot_path)
    logger.error(f"Blocking screenshot saved: {screenshot_path}")
    
    # Log page content for analysis
    content = await page.content()
    with open(f"blocking_content_{int(time.time())}.html", "w") as f:
        f.write(content)
    
    # Determine next action
    if attempt < 2:
        # Retry with longer delay
        backoff = 2 ** attempt * 10  # 10s, 20s, 40s
        logger.info(f"Retrying in {backoff} seconds...")
        await asyncio.sleep(backoff)
        return "retry"
    else:
        # Give up gracefully
        logger.error("Max retries reached - marking scraper as blocked")
        return "fail"
```

#### 6. Complete TripAdvisor Implementation

```python
class TripAdvisorScraper(BaseScraper):
    """TripAdvisor scraper with aggressive anti-blocking."""
    
    def __init__(self):
        super().__init__(
            source_name="tripadvisor",
            browser_type="camoufox",
            base_url="https://www.tripadvisor.com"
        )
        self.metrics = ScraperMetrics()
    
    async def scrape(self, location: str, **kwargs) -> List[Dict]:
        """Scrape with full anti-blocking measures."""
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Get geo ID
                geo_id = await self._lookup_geo_id(location)
                if not geo_id:
                    logger.error(f"Could not find geo ID for {location}")
                    return []
                
                # Initialize browser with stealth
                async with await self.get_browser(stealth_mode=True) as browser:
                    page = await browser.new_page()
                    
                    # Set random viewport
                    viewport = random.choice(VIEWPORTS)
                    await page.set_viewport_size(viewport)
                    
                    # Navigate to hotels page
                    url = f"{self.base_url}/Hotels-g{geo_id}-{location}-Hotels.html"
                    await page.goto(url, wait_until="networkidle")
                    
                    # Simulate human behavior
                    await simulate_realistic_browsing(page)
                    
                    # Check for blocking
                    if await is_tripadvisor_blocked(page):
                        action = await handle_tripadvisor_blocking(page, attempt)
                        if action == "retry":
                            continue
                        else:
                            self.metrics.record_attempt(False, True)
                            return []
                    
                    # Extract hotels
                    hotels = []
                    for page_num in range(3):  # Max 3 pages
                        # Extract current page
                        page_hotels = await self._extract_page(page)
                        hotels.extend(page_hotels)
                        
                        # Check for blocking after extraction
                        if await is_tripadvisor_blocked(page):
                            logger.warning(f"Blocked after page {page_num}")
                            break
                        
                        # Navigate to next page
                        if not await self._goto_next_page(page):
                            break
                        
                        # Long delay between pages
                        await asyncio.sleep(random.uniform(3, 6))
                    
                    # Success
                    self.metrics.record_attempt(True, False)
                    logger.info(f"TripAdvisor success rate: {self.metrics.success_rate:.2%}")
                    return hotels
                    
            except Exception as e:
                logger.error(f"TripAdvisor error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt * 10)
                    continue
        
        # All retries failed
        self.metrics.record_attempt(False, False)
        return []
```

---

## Part 2: eSewa Anti-Blocking Strategy

### Why eSewa Blocks

1. **Server Protection**: Prevent scraping load
2. **Rate Limiting**: Basic IP-based throttling
3. **Cloudflare**: May use Cloudflare protection

### Mitigation Strategy

#### 1. Progressive Browser Upgrade

```python
class ESewaHotelsScraper(BaseScraper):
    """eSewa scraper with progressive anti-blocking."""
    
    async def scrape(self, location: str, **kwargs) -> List[Dict]:
        """Try Playwright first, upgrade to Camoufox if blocked."""
        
        # Strategy 1: Try with Playwright (faster)
        logger.info("Attempting eSewa scrape with Playwright...")
        results = await self._scrape_with_browser("playwright", location)
        
        if results:
            return results
        
        # Strategy 2: Upgrade to Camoufox
        logger.warning("Playwright blocked, upgrading to Camoufox...")
        await asyncio.sleep(random.uniform(5, 10))
        results = await self._scrape_with_browser("camoufox", location)
        
        return results
    
    async def _scrape_with_browser(
        self, 
        browser_type: str, 
        location: str
    ) -> List[Dict]:
        """Scrape with specified browser type."""
        
        try:
            async with await self.get_browser(browser_type) as browser:
                page = await browser.new_page()
                
                # Navigate
                url = f"{self.base_url}/hotels?location={location}"
                await page.goto(url, wait_until="networkidle")
                
                # Check for blocking
                if await self._is_esewa_blocked(page):
                    logger.warning(f"eSewa blocking detected with {browser_type}")
                    return []
                
                # Extract hotels
                hotels = []
                while True:
                    # Longer delay
                    await asyncio.sleep(random.uniform(3, 5))
                    
                    page_hotels = await self._extract_page(page)
                    hotels.extend(page_hotels)
                    
                    # Check for blocking after each page
                    if await self._is_esewa_blocked(page):
                        logger.warning("eSewa blocking detected mid-scrape")
                        break
                    
                    # Next page
                    if not await self._goto_next_page(page):
                        break
                
                return hotels
                
        except Exception as e:
            logger.error(f"eSewa scraping error with {browser_type}: {e}")
            return []
    
    async def _is_esewa_blocked(self, page) -> bool:
        """Detect eSewa blocking."""
        
        content = await page.content()
        
        # Cloudflare challenge
        if "checking your browser" in content.lower():
            return True
        
        # Rate limiting
        if "too many requests" in content.lower():
            return True
        
        # Access denied
        if "access denied" in content.lower():
            return True
        
        # Suspiciously small page
        if len(content) < 2000:
            return True
        
        return False
```

---

## Part 3: Success Rate Monitoring

### Implementation

```python
class ScraperMetrics:
    """Track and report scraper performance."""
    
    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name
        self.attempts = 0
        self.successes = 0
        self.blocks = 0
        self.errors = 0
    
    def record_attempt(self, success: bool, blocked: bool, error: bool = False):
        """Record scraping attempt."""
        self.attempts += 1
        
        if success:
            self.successes += 1
        if blocked:
            self.blocks += 1
        if error:
            self.errors += 1
        
        # Log metrics
        logger.info(f"{self.scraper_name} Metrics: "
                   f"Success: {self.success_rate:.1%}, "
                   f"Block: {self.block_rate:.1%}, "
                   f"Error: {self.error_rate:.1%}")
    
    @property
    def success_rate(self) -> float:
        return self.successes / self.attempts if self.attempts > 0 else 0.0
    
    @property
    def block_rate(self) -> float:
        return self.blocks / self.attempts if self.attempts > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        return self.errors / self.attempts if self.attempts > 0 else 0.0
    
    def should_disable(self) -> bool:
        """Determine if scraper should be disabled."""
        # Disable if success rate < 30% after 10 attempts
        if self.attempts >= 10 and self.success_rate < 0.3:
            logger.error(f"{self.scraper_name} success rate too low: {self.success_rate:.1%}")
            return True
        return False
```

### Monitoring Dashboard

Add to admin panel:

```python
# backend/routers/admin.py

@router.get("/scraper-metrics")
async def get_scraper_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get scraper performance metrics."""
    
    metrics = {
        "agoda": scraper_registry.get_metrics("agoda"),
        "tripadvisor": scraper_registry.get_metrics("tripadvisor"),
        "esewa": scraper_registry.get_metrics("esewa"),
        "nepalyp": scraper_registry.get_metrics("nepalyp")
    }
    
    return metrics
```

---

## Part 4: Fallback Strategies

### If All Else Fails

#### 1. Mark as Experimental

```python
# In database seed
sources = [
    {
        "name": "TripAdvisor",
        "is_active": False,  # Disabled by default
        "is_experimental": True,
        "warning": "High blocking risk - enable at your own risk"
    }
]
```

#### 2. Reduce Scraping Frequency

```python
# Limit to once per day per location
SCRAPING_LIMITS = {
    "tripadvisor": {
        "max_per_day": 5,
        "cooldown_hours": 24
    }
}
```

#### 3. Consider Paid Solutions

- **Residential Proxies**: Bright Data, Oxylabs ($50-500/month)
- **CAPTCHA Solving**: 2Captcha, Anti-Captcha ($1-3 per 1000 CAPTCHAs)
- **Scraping APIs**: ScraperAPI, Zyte ($29-299/month)

---

## Part 5: Testing Anti-Blocking Features

### Unit Tests

```python
# backend/tests/test_anti_blocking.py

@pytest.mark.asyncio
async def test_blocking_detection():
    """Test blocking detection works."""
    scraper = TripAdvisorScraper()
    
    # Mock blocked page
    blocked_html = """
    <html>
        <body>
            <h1>Access Denied</h1>
            <p>Unusual traffic detected</p>
        </body>
    </html>
    """
    
    # Should detect blocking
    assert await scraper._is_blocked_from_html(blocked_html)

@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry with exponential backoff."""
    scraper = TripAdvisorScraper()
    
    start = time.time()
    results = await scraper.scrape_with_retry("Kathmandu", max_retries=3)
    duration = time.time() - start
    
    # Should take at least 35 seconds (5 + 10 + 20)
    assert duration >= 35

@pytest.mark.asyncio
async def test_browser_upgrade():
    """Test eSewa browser upgrade strategy."""
    scraper = ESewaHotelsScraper()
    
    # Should try Playwright first, then Camoufox
    results = await scraper.scrape("Kathmandu")
    
    # Verify both browsers were attempted
    assert scraper.playwright_attempted
    assert scraper.camoufox_attempted
```

---

## Part 6: Debugging Blocked Scrapers

### When Scraper Gets Blocked

1. **Check Screenshots**: Look in project root for `blocking_*.png`
2. **Check HTML Dumps**: Look for `blocking_content_*.html`
3. **Check Logs**: Search for "blocking detected" messages
4. **Verify Camoufox**: Ensure Camoufox is properly installed
5. **Test Manually**: Try visiting site in regular browser from same IP

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Immediate blocking | Datacenter IP | Use residential proxy |
| CAPTCHA every time | Fingerprint detected | Update Camoufox, randomize more |
| Works once, then blocks | Rate limiting | Increase delays, reduce frequency |
| Empty results | Wrong selectors | Update selectors in database |
| Timeout errors | Site too slow | Increase timeout, check network |

---

## Summary Checklist

Before deploying any scraper to production:

- [ ] Blocking detection implemented and tested
- [ ] Retry logic with exponential backoff
- [ ] Human behavior simulation (for high-risk scrapers)
- [ ] Success rate monitoring enabled
- [ ] Screenshots captured on blocking
- [ ] Graceful failure handling (no crashes)
- [ ] Metrics logged for monitoring
- [ ] Admin can view success rates
- [ ] Fallback strategy documented
- [ ] Tests pass for anti-blocking features

---

**Document Version**: 1.0  
**Last Updated**: April 29, 2026  
**Status**: Ready for Implementation

**Remember**: Bot detection is an arms race. These strategies work today but may need updates as sites improve their detection. Monitor success rates and be prepared to adapt.
