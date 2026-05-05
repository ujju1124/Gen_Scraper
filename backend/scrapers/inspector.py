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
        
        # Reload page to ensure fresh state
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
        confidence = await self.compute_confidence(element, field_hint, page_html)
        
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
        Find element on page matching field_hint value.
        
        Tries selectors in priority order:
        1. data-testid attribute
        2. ARIA role + accessible name
        3. Structural XPath
        4. CSS selector
        
        Args:
            page: Playwright page object
            field_hint: Example value to search for
            field_name: Name of the field (for context)
            
        Returns:
            Tuple of (element, selector, selector_type) or (None, None, None)
        """
        # Priority 1: data-testid
        try:
            # Search for elements with data-testid containing the field name
            testid_selector = f"[data-testid*='{field_name}']"
            element = await page.query_selector(testid_selector)
            if element:
                # Verify element contains the hint text
                text_content = await element.text_content()
                if text_content and field_hint.lower() in text_content.lower():
                    return element, testid_selector, "testid"
        except Exception as e:
            logger.debug("inspector.testid_search_failed", error=str(e))
        
        # Priority 2: ARIA role + accessible name
        try:
            # Try common ARIA roles
            for role in ["heading", "link", "button", "textbox", "img"]:
                aria_selector = f"[role='{role}']"
                elements = await page.query_selector_all(aria_selector)
                
                for element in elements:
                    # Check accessible name or text content
                    text_content = await element.text_content()
                    aria_label = await element.get_attribute("aria-label")
                    
                    if text_content and field_hint.lower() in text_content.lower():
                        return element, aria_selector, "role"
                    if aria_label and field_hint.lower() in aria_label.lower():
                        return element, aria_selector, "role"
        except Exception as e:
            logger.debug("inspector.aria_search_failed", error=str(e))
        
        # Priority 3: Structural XPath (search by text content)
        try:
            # Use XPath to find elements containing the hint text
            xpath_selector = f"//*[contains(text(), '{field_hint}')]"
            element = await page.query_selector(f"xpath={xpath_selector}")
            if element:
                return element, xpath_selector, "xpath"
        except Exception as e:
            logger.debug("inspector.xpath_search_failed", error=str(e))
        
        # Priority 4: CSS selector (last resort - search by class or tag)
        try:
            # Get all elements and search by text content
            all_elements = await page.query_selector_all("*")
            for element in all_elements:
                text_content = await element.text_content()
                if text_content and field_hint.lower() in text_content.lower():
                    # Try to generate a CSS selector for this element
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                    class_name = await element.get_attribute("class")
                    
                    if class_name:
                        css_selector = f"{tag_name}.{class_name.split()[0]}"
                    else:
                        css_selector = tag_name
                    
                    return element, css_selector, "css"
        except Exception as e:
            logger.debug("inspector.css_search_failed", error=str(e))
        
        # No element found
        return None, None, None
    
    async def compute_confidence(
        self,
        element: ElementHandle,
        field_hint: str,
        page_html: str
    ) -> float:
        """
        Compute confidence score for a found element.
        
        Scoring algorithm:
        - +0.5 for data-testid attribute
        - +0.3 for ARIA role + accessible name match
        - +0.2 for XPath structure match
        - -0.3 if hint appears >3 times on page (ambiguous)
        
        Score is clamped to [0.0, 1.0].
        
        Args:
            element: Found element
            field_hint: Example value that was searched for
            page_html: Full page HTML content
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # +0.5 for data-testid
        testid = await element.get_attribute("data-testid")
        if testid:
            score += self.CONFIDENCE_TESTID
            logger.debug("inspector.confidence_testid", testid=testid, score=score)
        
        # +0.3 for ARIA role + accessible name match
        role = await element.get_attribute("role")
        aria_label = await element.get_attribute("aria-label")
        if role and (aria_label or await element.text_content()):
            score += self.CONFIDENCE_ARIA
            logger.debug("inspector.confidence_aria", role=role, score=score)
        
        # +0.2 for structural XPath match
        # Check if element has a stable position in DOM (has ID or unique class)
        element_id = await element.get_attribute("id")
        class_name = await element.get_attribute("class")
        if element_id or (class_name and len(class_name.split()) == 1):
            score += self.CONFIDENCE_XPATH
            logger.debug("inspector.confidence_xpath", score=score)
        
        # -0.3 if hint appears >3 times (ambiguous)
        hint_count = page_html.lower().count(field_hint.lower())
        if hint_count > self.AMBIGUITY_THRESHOLD:
            score -= self.AMBIGUITY_PENALTY
            logger.debug(
                "inspector.confidence_ambiguity_penalty",
                hint_count=hint_count,
                penalty=self.AMBIGUITY_PENALTY,
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
