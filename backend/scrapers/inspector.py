"""
Inspector and AUTO Reheal Implementation for Web Scraping Portal Phase 2

This module implements the AUTO reheal logic that attempts to automatically
fix broken selectors by:
1. Reloading the live page
2. Searching for elements using field_hints
3. Computing confidence scores based on selector quality
4. Updating selectors if confidence ≥ 0.7
5. Falling back to MANUAL mode if confidence < 0.7
"""

from typing import Optional, Tuple
from datetime import datetime

import structlog
from sqlalchemy.orm import Session
from playwright.async_api import Page, ElementHandle

from models.scraper_selector import ScraperSelector
from models.selector_heal_log import SelectorHealLog
from models.source import Source

logger = structlog.get_logger()


class Inspector:
    """
    Implements AUTO reheal logic for broken selectors.
    
    The Inspector attempts to automatically find and update broken selectors
    by searching the live page for elements matching field_hints and computing
    confidence scores based on selector quality indicators.
    """
    
    # Confidence scoring weights
    CONFIDENCE_TESTID = 0.5
    CONFIDENCE_ARIA = 0.3
    CONFIDENCE_XPATH = 0.2
    AMBIGUITY_PENALTY = 0.3
    AMBIGUITY_THRESHOLD = 3
    
    # Confidence threshold for AUTO reheal
    CONFIDENCE_THRESHOLD = 0.7
    
    # Maximum HTML snapshot size (200KB)
    MAX_HTML_SIZE = 200 * 1024
    
    def __init__(self, db: Session):
        """
        Initialize the Inspector.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL for comparison.
        
        Examples:
            https://www.booking.com/hotels -> booking.com
            https://booking.com/search -> booking.com
            http://www.example.com:8080/path -> example.com
        
        Args:
            url: Full URL string
            
        Returns:
            Domain without protocol, www, or port
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path  # netloc for full URLs, path for partial
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain.lower()
    
    async def heal(
        self,
        page: Page,
        source_id: int,
        field_name: str
    ) -> Optional[str]:
        """
        Attempt to heal a broken selector using AUTO reheal logic.
        
        This is the main entry point for the healing process. It:
        1. Loads the source and field_hint
        2. Reloads the page
        3. Finds the element using field_hint
        4. Computes confidence score
        5. Updates selector if confidence ≥ 0.7
        6. Falls back to MANUAL if confidence < 0.7
        
        Args:
            page: Playwright page object (already loaded)
            source_id: ID of the source
            field_name: Name of the field with broken selector
            
        Returns:
            New selector string if healed successfully, None otherwise
        """
        # Load source
        source = self.db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error("inspector.source_not_found", source_id=source_id)
            return None
        
        # Get field hint
        field_hints = source.field_hints or {}
        field_hint = field_hints.get(field_name)
        
        if not field_hint:
            logger.warning(
                "inspector.no_field_hint",
                source_id=source_id,
                field_name=field_name
            )
            # Fall through to MANUAL
            await self._save_manual_fallback(page, source_id, field_name, None, None)
            return None
        
        # Get old selector
        old_selector_record = self.db.query(ScraperSelector).filter(
            ScraperSelector.source_id == source_id,
            ScraperSelector.field_name == field_name
        ).first()
        
        old_selector = old_selector_record.selector if old_selector_record else None
        
        # Check if page is already on the correct domain
        current_url = page.url
        source_domain = self._extract_domain(source.base_url)
        current_domain = self._extract_domain(current_url)
        
        # Only reload if we're not already on the correct domain
        # During active scrapes, the page is already loaded and reloading causes timeouts
        if current_domain != source_domain:
            logger.info(
                "inspector.reloading_page",
                source_id=source_id,
                field_name=field_name,
                current_domain=current_domain,
                expected_domain=source_domain
            )
            try:
                await page.reload(wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.error(
                    "inspector.reload_failed",
                    source_id=source_id,
                    field_name=field_name,
                    error=str(e)
                )
                return None
        else:
            logger.info(
                "inspector.skip_reload",
                source_id=source_id,
                field_name=field_name,
                reason="already_on_correct_domain",
                current_url=current_url
            )
        
        # Find element by hint
        element, selector, selector_type = await self.find_element_by_hint(
            page,
            field_hint,
            field_name
        )
        
        if not element or not selector:
            logger.warning(
                "inspector.element_not_found",
                source_id=source_id,
                field_name=field_name,
                field_hint=field_hint
            )
            
            # Log failure with structured event
            logger.error(
                "selector.heal_failed",
                source_id=source_id,
                field_name=field_name,
                confidence=0.0,
                heal_mode="AUTO",
                reason="element_not_found"
            )
            
            # Fall through to MANUAL
            await self._save_manual_fallback(page, source_id, field_name, old_selector, 0.0)
            return None
        
        # Compute confidence
        page_html = await page.content()
        confidence = await self.compute_confidence(element, field_hint, page_html, selector_type)
        
        logger.info(
            "inspector.confidence_computed",
            source_id=source_id,
            field_name=field_name,
            confidence=confidence,
            selector_type=selector_type
        )
        
        # Check if confidence meets threshold
        if confidence >= self.CONFIDENCE_THRESHOLD:
            # Update selector in database
            if old_selector_record:
                old_selector_record.selector = selector
                old_selector_record.selector_type = selector_type
                old_selector_record.verified_at = datetime.utcnow()
            else:
                # Create new selector record
                new_selector_record = ScraperSelector(
                    source_id=source_id,
                    field_name=field_name,
                    selector=selector,
                    selector_type=selector_type,
                    verified_at=datetime.utcnow(),
                    is_active=True
                )
                self.db.add(new_selector_record)
            
            # Log successful heal
            heal_log = SelectorHealLog(
                source_id=source_id,
                field_name=field_name,
                old_selector=old_selector,
                new_selector=selector,
                trigger="auto_reheal",
                confidence=confidence,
                status="RESOLVED",
                resolved_at=datetime.utcnow()
            )
            self.db.add(heal_log)
            self.db.commit()
            
            # Emit structured log event
            logger.info(
                "selector.healed",
                source_id=source_id,
                field_name=field_name,
                old_selector=old_selector,
                new_selector=selector,
                confidence=confidence,
                heal_mode="AUTO",
                selector_type=selector_type
            )
            
            return selector
        else:
            # Confidence too low, fall through to MANUAL
            logger.warning(
                "inspector.confidence_too_low",
                source_id=source_id,
                field_name=field_name,
                confidence=confidence,
                threshold=self.CONFIDENCE_THRESHOLD
            )
            
            # Log failure with structured event
            logger.error(
                "selector.heal_failed",
                source_id=source_id,
                field_name=field_name,
                confidence=confidence,
                heal_mode="AUTO",
                reason="confidence_below_threshold"
            )
            
            await self._save_manual_fallback(
                page,
                source_id,
                field_name,
                old_selector,
                confidence
            )
            return None
    
    async def find_element_by_hint(
        self,
        page: Page,
        field_hint: str,
        field_name: str
    ) -> Tuple[Optional[ElementHandle], Optional[str], Optional[str]]:
        """
        Find element on page using multi-strategy search.
        
        STRATEGY 1: ARIA-label search (highest confidence 0.85)
        STRATEGY 2: data-testid search (confidence 0.90)
        STRATEGY 3: Field-specific structural patterns (confidence 0.75-0.80)
        STRATEGY 4: Schema.org microdata (confidence 0.80)
        
        Args:
            page: Playwright page object
            field_hint: Example value to search for (may not be used for structural search)
            field_name: Name of the field (for context)
            
        Returns:
            Tuple of (element, selector, selector_type) or (None, None, None)
        """
        
        # STRATEGY 1: ARIA-label search (confidence 0.85)
        try:
            # Search by aria-label containing field name or hint
            aria_selectors = [
                f'[aria-label*="{field_name}"]',
                f'[aria-label*="{field_name.replace("_", " ")}"]',
            ]
            
            # Add hint-based search if hint is short enough
            if len(field_hint) <= 20:
                aria_selectors.append(f'[aria-label*="{field_hint[:10]}"]')
            
            for aria_selector in aria_selectors:
                try:
                    element = await page.query_selector(aria_selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 0:
                            logger.info(
                                "inspector.aria_label_match",
                                field_name=field_name,
                                selector=aria_selector,
                                confidence=0.85
                            )
                            return element, aria_selector, "aria-label"
                except:
                    continue
        except Exception as e:
            logger.debug("inspector.aria_label_search_failed", field_name=field_name, error=str(e))
        
        # STRATEGY 2: data-testid search (confidence 0.90)
        try:
            testid_selectors = [
                f'[data-testid*="{field_name}"]',
                f'[data-testid*="{field_name.replace("_", "-")}"]',
                f'[data-testid*="{field_name.replace("_", "")}"]',
            ]
            
            for testid_selector in testid_selectors:
                try:
                    element = await page.query_selector(testid_selector)
                    if element:
                        logger.info(
                            "inspector.testid_match",
                            field_name=field_name,
                            selector=testid_selector,
                            confidence=0.90
                        )
                        return element, testid_selector, "testid"
                except:
                    continue
        except Exception as e:
            logger.debug("inspector.testid_search_failed", field_name=field_name, error=str(e))
        
        # STRATEGY 3: Field-specific structural patterns (confidence 0.75-0.80)
        try:
            if field_name == 'name':
                # Business names: h1, h2, h3, or elements with "title"/"name" in class
                # FIX 1: Added NepalYP-specific patterns
                # FIX 2: Added Booking.com data-testid patterns (highest priority)
                selectors = [
                    # Booking.com specific (try first)
                    '[data-testid="title"]',
                    'div[data-testid="title"]',
                    'div[data-testid="title"] a',
                    # Generic patterns
                    'h1', 'h2', 'h3',
                    '[class*="title"]', '[class*="name"]', '[class*="Title"]', '[class*="Name"]',
                    '[data-testid*="name"]', '[data-testid*="title"]',
                    # NepalYP-specific patterns
                    'a[href*="/company/"]',
                    '.company-name', '.listing-title', '.biz-name', '.business-name',
                    'div[class*="name"] a',
                    'td a[href*="company"]',
                    'h3 a', 'h4 a',  # NepalYP uses h3/h4 not h1
                ]
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and len(text.strip()) > 2:
                            # Get more specific selector with class
                            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                            classes = await element.get_attribute('class')
                            if classes and tag_name in ['h1', 'h2', 'h3']:
                                first_class = classes.split()[0]
                                final_selector = f"{tag_name}.{first_class}"
                            else:
                                final_selector = selector
                            
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=final_selector,
                                confidence=0.80
                            )
                            return element, final_selector, "structural"
            
            elif field_name in ['rating', 'rating_overall']:
                # Ratings: spans/divs with "rating"/"score" in class or aria-label
                # FIX 2: Handle aria-hidden elements by checking parent aria-labels
                
                # GOOGLE MAPS FIX: Try specific Google Maps patterns first with high confidence
                try:
                    gmaps_elements = await page.query_selector_all(
                        '[aria-label*="stars"], '
                        '[aria-label*="Rated"], '
                        'span.MW4etd, '
                        '[jstcache] span[aria-label]'
                    )
                    for el in gmaps_elements:
                        # Check if element or parent has aria-label with digits
                        label = await el.get_attribute('aria-label')
                        if not label:
                            # Check parent
                            parent = await el.evaluate_handle("el => el.parentElement")
                            if parent:
                                label = await parent.get_attribute('aria-label')
                        
                        if label and any(c.isdigit() for c in label):
                            # Get text content to verify it's a rating
                            text = await el.text_content()
                            if text and any(c.isdigit() for c in text):
                                # Get selector
                                tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                                classes = await el.get_attribute('class')
                                if classes:
                                    first_class = classes.split()[0]
                                    final_selector = f"{tag_name}.{first_class}"
                                else:
                                    final_selector = tag_name
                                
                                logger.info(
                                    "inspector.gmaps_rating_match",
                                    field_name=field_name,
                                    selector=final_selector,
                                    confidence=0.85
                                )
                                return el, final_selector, "gmaps-rating"
                except Exception as e:
                    logger.debug("inspector.gmaps_rating_search_failed", error=str(e))
                
                selectors = [
                    '[class*="rating"]', '[class*="score"]', '[class*="Rating"]', '[class*="Score"]',
                    '[aria-label*="rating"]', '[aria-label*="star"]', '[aria-label*="Rating"]', '[aria-label*="Star"]',
                    '[data-testid*="rating"]', '[itemprop="ratingValue"]',
                    # Google Maps specific patterns
                    'span[aria-label*="star"]',
                    'span[aria-label*="out of"]',
                    '[class*="rating"] span',
                    'span.MW4etd',  # Google Maps current class
                    '[jslog*="rating"]',
                ]
                
                # First try direct selectors
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        # Verify it contains a number
                        if text and any(c.isdigit() for c in text):
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=selector,
                                confidence=0.75
                            )
                            return element, selector, "structural"
                
                # FIX 2: Search parent elements with aria-label (for aria-hidden children)
                try:
                    parent_elements = await page.query_selector_all('[aria-label*="star"], [aria-label*="rating"], [aria-label*="Star"], [aria-label*="Rating"]')
                    for parent in parent_elements:
                        # Get numeric text from aria-label
                        aria_text = await parent.get_attribute('aria-label')
                        if aria_text and any(c.isdigit() for c in aria_text):
                            # Check if parent has child spans (even if aria-hidden)
                            child_spans = await parent.query_selector_all('span')
                            if child_spans:
                                # Use first child span that has numeric content
                                for child in child_spans:
                                    child_text = await child.text_content()
                                    if child_text and any(c.isdigit() for c in child_text):
                                        # Get selector for this child
                                        tag_name = await child.evaluate("el => el.tagName.toLowerCase()")
                                        classes = await child.get_attribute('class')
                                        if classes:
                                            first_class = classes.split()[0]
                                            final_selector = f"{tag_name}.{first_class}"
                                        else:
                                            final_selector = f"{tag_name}"
                                        
                                        logger.info(
                                            "inspector.aria_parent_match",
                                            field_name=field_name,
                                            selector=final_selector,
                                            confidence=0.85
                                        )
                                        return child, final_selector, "aria-parent"
                except Exception as e:
                    logger.debug("inspector.aria_parent_search_failed", error=str(e))
            
            elif field_name == 'review_count':
                # Review counts: spans with "review" in aria-label or class, or numbers in parentheses
                selectors = [
                    'span[aria-label*="review"]', 'span[aria-label*="Review"]',
                    '[class*="review"][class*="count"]', '[class*="Review"][class*="Count"]',
                    '[data-testid*="review"]'
                ]
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and any(c.isdigit() for c in text):
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=selector,
                                confidence=0.75
                            )
                            return element, selector, "structural"
                
                # Fallback: look for patterns like "(1,234)" or "1234 reviews"
                all_spans = await page.query_selector_all('span, div')
                for element in all_spans:
                    text = await element.text_content()
                    if text:
                        text = text.strip()
                        # Match "(number)" or "number review"
                        if ('(' in text and ')' in text and any(c.isdigit() for c in text)) or \
                           ('review' in text.lower() and any(c.isdigit() for c in text)):
                            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                            classes = await element.get_attribute('class')
                            if classes:
                                first_class = classes.split()[0]
                                final_selector = f"{tag_name}.{first_class}"
                            else:
                                final_selector = f"{tag_name}"
                            
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=final_selector,
                                confidence=0.70
                            )
                            return element, final_selector, "structural"
            
            elif field_name in ['address', 'location']:
                # Addresses: address tag, itemprop, or class containing "address"/"location"
                # FIX 1: Added NepalYP-specific patterns
                selectors = [
                    'address',
                    '[itemprop="address"]', '[itemprop="streetAddress"]',
                    '[class*="address"]', '[class*="location"]', '[class*="Address"]', '[class*="Location"]',
                    '[data-testid*="address"]', '[data-testid*="location"]',
                    # NepalYP-specific patterns
                    '.address', '.location',
                    'span[class*="addr"]',
                    'div[class*="location"]',
                ]
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 5:
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=selector,
                                confidence=0.80
                            )
                            return element, selector, "structural"
            
            elif field_name in ['price', 'price_min', 'price_max']:
                # Prices: elements with "price"/"rate" in class or itemprop
                selectors = [
                    '[class*="price"]', '[class*="rate"]', '[class*="Price"]', '[class*="Rate"]',
                    '[data-testid*="price"]', '[itemprop="price"]', '[itemprop="priceRange"]'
                ]
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        # Verify it contains currency symbol or number
                        if text and (any(c.isdigit() for c in text) or '$' in text or '₹' in text or '€' in text):
                            logger.info(
                                "inspector.structural_match",
                                field_name=field_name,
                                selector=selector,
                                confidence=0.75
                            )
                            return element, selector, "structural"
            
            elif field_name in ['phone', 'phone_primary']:
                # Phone numbers: tel: links or itemprop
                # FIX 1: Added NepalYP-specific patterns
                selectors = [
                    'a[href^="tel:"]',
                    '[itemprop="telephone"]',
                    '[class*="phone"]', '[class*="Phone"]', '[class*="tel"]',
                    '[data-testid*="phone"]',
                    # NepalYP-specific patterns
                    '[class*="contact"]',
                    'span[class*="contact"]',
                    'div[class*="phone"] a',
                ]
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(
                            "inspector.structural_match",
                            field_name=field_name,
                            selector=selector,
                            confidence=0.80
                        )
                        return element, selector, "structural"
        
        except Exception as e:
            logger.debug("inspector.structural_search_failed", field_name=field_name, error=str(e))
        
        # STRATEGY 4: Schema.org microdata (confidence 0.80)
        try:
            # Map field names to itemprop values
            itemprop_map = {
                'name': ['name'],
                'address': ['address', 'streetAddress'],
                'phone': ['telephone'],
                'phone_primary': ['telephone'],
                'rating': ['ratingValue'],
                'rating_overall': ['ratingValue'],
                'review_count': ['reviewCount'],
                'price': ['price', 'priceRange'],
                'price_min': ['price', 'priceRange'],
            }
            
            if field_name in itemprop_map:
                for itemprop_value in itemprop_map[field_name]:
                    selector = f'[itemprop="{itemprop_value}"]'
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(
                            "inspector.itemprop_match",
                            field_name=field_name,
                            selector=selector,
                            confidence=0.80
                        )
                        return element, selector, "itemprop"
        except Exception as e:
            logger.debug("inspector.itemprop_search_failed", field_name=field_name, error=str(e))
        
        # No element found with any strategy
        logger.warning(
            "inspector.no_element_found",
            field_name=field_name,
            strategies_tried=["aria-label", "testid", "structural", "itemprop"]
        )
        return None, None, None
    
    async def compute_confidence(
        self,
        element: ElementHandle,
        field_hint: str,
        page_html: str,
        selector_type: Optional[str] = None
    ) -> float:
        """
        Compute confidence score for a found element.
        
        Scoring algorithm (updated for multi-strategy search):
        - aria-parent match: 0.85 (high) - NEW
        - data-testid match: 0.90 (very high)
        - aria-label match: 0.85 (high)
        - itemprop match: 0.80 (high)
        - structural match (h1, address, etc.): 0.75-0.80 (medium-high)
        - class*= match with field name: 0.70 (medium)
        - -0.15 if hint appears >10 times on page (ambiguous) - REDUCED PENALTY
        
        Score is clamped to [0.0, 1.0].
        
        Args:
            element: Found element
            field_hint: Example value that was searched for
            page_html: Full page HTML content
            selector_type: Optional selector type from find_element_by_hint (e.g., "aria-parent")
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Check selector_type first (passed from find_element_by_hint)
        if selector_type == "aria-parent":
            score = 0.85
            logger.debug("inspector.confidence_aria_parent", score=score)
            return score  # Return immediately for high confidence
        
        if selector_type == "gmaps-rating":
            score = 0.85
            logger.debug("inspector.confidence_gmaps_rating", score=score)
            return score  # Return immediately for high confidence
        
        # Check data-testid (0.90)
        testid = await element.get_attribute("data-testid")
        if testid:
            score = 0.90
            logger.debug("inspector.confidence_testid", testid=testid, score=score)
            return score  # Return immediately for highest confidence
        
        # Check aria-label (0.85)
        aria_label = await element.get_attribute("aria-label")
        if aria_label:
            score = 0.85
            logger.debug("inspector.confidence_aria_label", aria_label=aria_label[:50], score=score)
            return score  # Return immediately for high confidence
        
        # Check itemprop (0.80)
        itemprop = await element.get_attribute("itemprop")
        if itemprop:
            score = 0.80
            logger.debug("inspector.confidence_itemprop", itemprop=itemprop, score=score)
            return score  # Return immediately for high confidence
        
        # Check structural elements (0.75-0.80)
        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        if tag_name in ['h1', 'h2', 'address']:
            score = 0.80
            logger.debug("inspector.confidence_structural_tag", tag=tag_name, score=score)
        elif tag_name == 'h3':
            score = 0.75
            logger.debug("inspector.confidence_structural_tag", tag=tag_name, score=score)
        else:
            # Check for class-based match
            class_name = await element.get_attribute("class")
            if class_name:
                # Check if class contains field-related keywords
                class_lower = class_name.lower()
                field_keywords = ['name', 'title', 'rating', 'review', 'address', 'location', 'price', 'phone']
                if any(keyword in class_lower for keyword in field_keywords):
                    score = 0.70
                    logger.debug("inspector.confidence_class_match", class_name=class_name[:50], score=score)
                else:
                    score = 0.65
                    logger.debug("inspector.confidence_generic", score=score)
            else:
                # FIX 3: Check for tel: link (high confidence for phone)
                href = await element.get_attribute("href")
                if href and href.startswith("tel:"):
                    score = 0.85
                    logger.debug("inspector.confidence_tel_link", score=score)
                else:
                    score = 0.60
                    logger.debug("inspector.confidence_no_attributes", score=score)
        
        # Apply ambiguity penalty (reduced)
        # Only penalize if hint appears >10 times (was 5)
        hint_count = page_html.lower().count(field_hint.lower()) if field_hint else 0
        if hint_count > 10:
            penalty = 0.15  # Reduced from 0.20
            score -= penalty
            logger.debug(
                "inspector.confidence_ambiguity_penalty",
                hint_count=hint_count,
                penalty=penalty,
                score=score
            )
        
        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))
        
        return score
    
    async def _save_manual_fallback(
        self,
        page: Page,
        source_id: int,
        field_name: str,
        old_selector: Optional[str],
        confidence: Optional[float]
    ) -> None:
        """
        Save HTML snapshot for MANUAL reheal.
        
        This is called when AUTO reheal fails or confidence is too low.
        Saves page HTML (max 200KB) to selector_heal_log with status=PENDING.
        
        Args:
            page: Playwright page object
            source_id: ID of the source
            field_name: Name of the field
            old_selector: Previous selector that failed
            confidence: Confidence score (if computed)
        """
        try:
            # Get page HTML
            html_content = await page.content()
            
            # Truncate to max size
            if len(html_content) > self.MAX_HTML_SIZE:
                html_content = html_content[:self.MAX_HTML_SIZE]
                logger.warning(
                    "inspector.html_truncated",
                    source_id=source_id,
                    field_name=field_name,
                    original_size=len(html_content),
                    truncated_size=self.MAX_HTML_SIZE
                )
            
            # Save to heal log
            heal_log = SelectorHealLog(
                source_id=source_id,
                field_name=field_name,
                old_selector=old_selector,
                new_selector=None,
                trigger="auto_reheal",
                confidence=confidence,
                status="PENDING",
                html_snapshot=html_content
            )
            self.db.add(heal_log)
            self.db.commit()
            
            logger.info(
                "inspector.manual_fallback_saved",
                source_id=source_id,
                field_name=field_name,
                confidence=confidence,
                html_size=len(html_content)
            )
            
        except Exception as e:
            logger.error(
                "inspector.manual_fallback_failed",
                source_id=source_id,
                field_name=field_name,
                error=str(e)
            )
