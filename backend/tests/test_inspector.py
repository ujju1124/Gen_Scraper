"""
Unit tests for Inspector and AUTO reheal logic.

Tests cover:
- Confidence scoring with various element combinations
- Selector priority (testid > ARIA > XPath > CSS)
- Ambiguity penalty (hint appears >3 times)
- Manual fallback behavior
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from scrapers.inspector import Inspector
from models.scraper_selector import ScraperSelector
from models.selector_heal_log import SelectorHealLog
from models.source import Source


class TestInspector:
    """Test suite for Inspector class."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def inspector(self, db_session):
        """Create Inspector instance."""
        return Inspector(db_session)
    
    @pytest.fixture
    def mock_element(self):
        """Create mock Playwright element."""
        element = AsyncMock()
        element.get_attribute = AsyncMock(return_value=None)
        element.text_content = AsyncMock(return_value="Test Content")
        element.evaluate = AsyncMock(return_value="div")
        return element
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
        page.reload = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        return page
    
    # ========================================================================
    # Confidence Scoring Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_compute_confidence_with_testid(self, inspector, mock_element):
        """Test confidence scoring with data-testid attribute."""
        # Element has data-testid
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": "hotel-name",
            "role": None,
            "aria-label": None,
            "id": None,
            "class": None
        }.get(attr))
        
        page_html = "<html><body>Hotel Himalaya</body></html>"
        confidence = await inspector.compute_confidence(
            mock_element,
            "Hotel Himalaya",
            page_html
        )
        
        # Should get +0.5 for testid
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_compute_confidence_with_aria(self, inspector, mock_element):
        """Test confidence scoring with ARIA role + accessible name."""
        # Element has ARIA role and label
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": None,
            "role": "heading",
            "aria-label": "Hotel Name",
            "id": None,
            "class": None
        }.get(attr))
        
        page_html = "<html><body>Hotel Himalaya</body></html>"
        confidence = await inspector.compute_confidence(
            mock_element,
            "Hotel Himalaya",
            page_html
        )
        
        # Should get +0.3 for ARIA
        assert confidence == 0.3
    
    @pytest.mark.asyncio
    async def test_compute_confidence_with_xpath_structure(self, inspector, mock_element):
        """Test confidence scoring with structural XPath match."""
        # Element has unique ID
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": None,
            "role": None,
            "aria-label": None,
            "id": "hotel-name",
            "class": None
        }.get(attr))
        
        page_html = "<html><body>Hotel Himalaya</body></html>"
        confidence = await inspector.compute_confidence(
            mock_element,
            "Hotel Himalaya",
            page_html
        )
        
        # Should get +0.2 for XPath structure
        assert confidence == 0.2
    
    @pytest.mark.asyncio
    async def test_compute_confidence_high_score(self, inspector, mock_element):
        """Test high confidence score with multiple indicators."""
        # Element has testid, ARIA, and unique ID
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": "hotel-name",
            "role": "heading",
            "aria-label": "Hotel Name",
            "id": "hotel-name",
            "class": None
        }.get(attr))
        
        page_html = "<html><body>Hotel Himalaya</body></html>"
        confidence = await inspector.compute_confidence(
            mock_element,
            "Hotel Himalaya",
            page_html
        )
        
        # Should get +0.5 (testid) +0.3 (ARIA) +0.2 (XPath) = 1.0
        assert confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_compute_confidence_ambiguity_penalty(self, inspector, mock_element):
        """Test ambiguity penalty when hint appears >3 times."""
        # Element has testid
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": "hotel-name",
            "role": None,
            "aria-label": None,
            "id": None,
            "class": None
        }.get(attr))
        
        # Hint appears 5 times in page HTML
        page_html = """
        <html><body>
            <div>Hotel</div>
            <div>Hotel</div>
            <div>Hotel</div>
            <div>Hotel</div>
            <div>Hotel</div>
        </body></html>
        """
        
        confidence = await inspector.compute_confidence(
            mock_element,
            "Hotel",
            page_html
        )
        
        # Should get +0.5 (testid) -0.3 (ambiguity) = 0.2
        assert confidence == 0.2
    
    @pytest.mark.asyncio
    async def test_compute_confidence_clamped_to_zero(self, inspector, mock_element):
        """Test confidence score is clamped to 0.0."""
        # Element has no indicators
        mock_element.get_attribute = AsyncMock(return_value=None)
        
        # Hint appears 5 times (ambiguity penalty)
        page_html = """
        <html><body>
            <div>Test</div>
            <div>Test</div>
            <div>Test</div>
            <div>Test</div>
            <div>Test</div>
        </body></html>
        """
        
        confidence = await inspector.compute_confidence(
            mock_element,
            "Test",
            page_html
        )
        
        # Should get 0.0 - 0.3 = -0.3, clamped to 0.0
        assert confidence == 0.0
    
    # ========================================================================
    # Selector Priority Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_find_element_by_hint_testid_priority(self, inspector, mock_page, mock_element):
        """Test that data-testid has highest priority."""
        # Mock testid selector to return element
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_element.text_content = AsyncMock(return_value="Hotel Himalaya")
        
        element, selector, selector_type = await inspector.find_element_by_hint(
            mock_page,
            "Hotel Himalaya",
            "name"
        )
        
        assert element is not None
        assert selector == "[data-testid*='name']"
        assert selector_type == "testid"
    
    @pytest.mark.asyncio
    async def test_find_element_by_hint_aria_priority(self, inspector, mock_page, mock_element):
        """Test that ARIA has second priority."""
        # Testid fails, ARIA succeeds
        async def query_selector_side_effect(selector):
            if "data-testid" in selector:
                return None
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_element.text_content = AsyncMock(return_value="Hotel Himalaya")
        mock_element.get_attribute = AsyncMock(return_value=None)
        
        element, selector, selector_type = await inspector.find_element_by_hint(
            mock_page,
            "Hotel Himalaya",
            "name"
        )
        
        assert element is not None
        assert selector_type == "role"
    
    @pytest.mark.asyncio
    async def test_find_element_by_hint_xpath_priority(self, inspector, mock_page, mock_element):
        """Test that XPath has third priority."""
        # Testid and ARIA fail, XPath succeeds
        async def query_selector_side_effect(selector):
            if "xpath=" in selector:
                return mock_element
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        element, selector, selector_type = await inspector.find_element_by_hint(
            mock_page,
            "Hotel Himalaya",
            "name"
        )
        
        assert element is not None
        assert selector_type == "xpath"
    
    @pytest.mark.asyncio
    async def test_find_element_by_hint_not_found(self, inspector, mock_page):
        """Test when element is not found."""
        # All selectors fail
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        element, selector, selector_type = await inspector.find_element_by_hint(
            mock_page,
            "Nonexistent",
            "name"
        )
        
        assert element is None
        assert selector is None
        assert selector_type is None
    
    # ========================================================================
    # Heal Method Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_heal_success_high_confidence(self, inspector, db_session, mock_page, mock_element):
        """Test successful heal with confidence ≥ 0.7."""
        # Setup source with field_hints
        source = Source(
            id=1,
            name="booking_com",
            display_name="Booking.com",
            base_url="https://www.booking.com",
            heal_mode="AUTO",
            field_hints={"name": "Hotel Himalaya"}
        )
        
        # Setup old selector
        old_selector = ScraperSelector(
            source_id=1,
            field_name="name",
            selector=".old-selector",
            selector_type="css",
            is_active=True
        )
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            source,  # First call for Source
            old_selector  # Second call for ScraperSelector
        ]
        
        # Mock element finding with high confidence
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            "data-testid": "hotel-name",
            "role": "heading",
            "aria-label": "Hotel Name",
            "id": "hotel-name",
            "class": None
        }.get(attr))
        
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_element.text_content = AsyncMock(return_value="Hotel Himalaya")
        
        # Mock find_element_by_hint
        with patch.object(inspector, 'find_element_by_hint', return_value=(
            mock_element,
            "[data-testid='hotel-name']",
            "testid"
        )):
            result = await inspector.heal(mock_page, 1, "name")
        
        # Should return new selector
        assert result == "[data-testid='hotel-name']"
        
        # Should update selector in database
        assert old_selector.selector == "[data-testid='hotel-name']"
        assert old_selector.selector_type == "testid"
        
        # Should save heal log
        assert db_session.add.called
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_heal_failure_low_confidence(self, inspector, db_session, mock_page, mock_element):
        """Test heal failure with confidence < 0.7."""
        # Setup source with field_hints
        source = Source(
            id=1,
            name="booking_com",
            display_name="Booking.com",
            base_url="https://www.booking.com",
            heal_mode="AUTO",
            field_hints={"name": "Hotel"}
        )
        
        old_selector = ScraperSelector(
            source_id=1,
            field_name="name",
            selector=".old-selector",
            selector_type="css",
            is_active=True
        )
        
        db_session.query.return_value.filter.return_value.first.side_effect = [
            source,
            old_selector
        ]
        
        # Mock element finding with low confidence (no indicators, high ambiguity)
        mock_element.get_attribute = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="Hotel Hotel Hotel Hotel Hotel")
        
        with patch.object(inspector, 'find_element_by_hint', return_value=(
            mock_element,
            ".some-selector",
            "css"
        )):
            result = await inspector.heal(mock_page, 1, "name")
        
        # Should return None (failed)
        assert result is None
        
        # Should save manual fallback
        assert db_session.add.called
        assert db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_heal_no_field_hint(self, inspector, db_session, mock_page):
        """Test heal when field_hint is missing."""
        # Setup source without field_hints
        source = Source(
            id=1,
            name="booking_com",
            display_name="Booking.com",
            base_url="https://www.booking.com",
            heal_mode="AUTO",
            field_hints={}
        )
        
        db_session.query.return_value.filter.return_value.first.return_value = source
        
        result = await inspector.heal(mock_page, 1, "name")
        
        # Should return None and fall through to MANUAL
        assert result is None
    
    @pytest.mark.asyncio
    async def test_heal_element_not_found(self, inspector, db_session, mock_page):
        """Test heal when element is not found."""
        # Setup source with field_hints
        source = Source(
            id=1,
            name="booking_com",
            display_name="Booking.com",
            base_url="https://www.booking.com",
            heal_mode="AUTO",
            field_hints={"name": "Hotel Himalaya"}
        )
        
        old_selector = ScraperSelector(
            source_id=1,
            field_name="name",
            selector=".old-selector",
            selector_type="css",
            is_active=True
        )
        
        # Mock returns source first, then old_selector
        db_session.query.return_value.filter.return_value.first.side_effect = [
            source,
            old_selector
        ]
        
        # Mock element not found
        with patch.object(inspector, 'find_element_by_hint', return_value=(None, None, None)):
            result = await inspector.heal(mock_page, 1, "name")
        
        # Should return None and save manual fallback
        assert result is None
    
    # ========================================================================
    # Manual Fallback Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_manual_fallback_saves_html(self, inspector, db_session, mock_page):
        """Test that manual fallback saves HTML snapshot."""
        mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        
        await inspector._save_manual_fallback(
            mock_page,
            1,
            "name",
            ".old-selector",
            0.4
        )
        
        # Should save heal log with PENDING status
        assert db_session.add.called
        assert db_session.commit.called
        
        # Verify heal log was created
        heal_log_call = db_session.add.call_args[0][0]
        assert isinstance(heal_log_call, SelectorHealLog)
        assert heal_log_call.status == "PENDING"
        assert heal_log_call.html_snapshot is not None
    
    @pytest.mark.asyncio
    async def test_manual_fallback_truncates_large_html(self, inspector, db_session, mock_page):
        """Test that HTML is truncated to 200KB."""
        # Create HTML larger than 200KB
        large_html = "<html><body>" + ("x" * 300000) + "</body></html>"
        mock_page.content = AsyncMock(return_value=large_html)
        
        await inspector._save_manual_fallback(
            mock_page,
            1,
            "name",
            ".old-selector",
            0.4
        )
        
        # Verify HTML was truncated
        heal_log_call = db_session.add.call_args[0][0]
        assert len(heal_log_call.html_snapshot) == Inspector.MAX_HTML_SIZE
