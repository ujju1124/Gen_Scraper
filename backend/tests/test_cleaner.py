"""
Unit tests for CleaningPipeline (Phase 2)

Tests the 7-step cleaning pipeline:
1. Save raw results
2. Normalize data
3. Within-job deduplication
4. Cross-job deduplication
5. Validate fields
6. Compute completeness
7. Save cleaned results
"""

import pytest
import hashlib
import uuid
from decimal import Decimal
from sqlalchemy import text

from scrapers.cleaner import CleaningPipeline
from models.raw_result import RawResult
from models.cleaned_result import CleanedResult
from models.scrape_job import ScrapeJob


@pytest.fixture
def create_test_job(db_session, test_user):
    """Helper fixture to create a test scrape job"""
    def _create_job(job_id=None):
        if job_id is None:
            job_id = uuid.uuid4()
        elif isinstance(job_id, str):
            job_id = uuid.UUID(job_id)
        
        job = ScrapeJob(
            id=job_id,
            user_id=test_user.id,  # Use the test_user fixture
            category_id=1,
            location="Test Location",
            status="QUEUED"
        )
        db_session.add(job)
        db_session.commit()
        return str(job.id)
    
    return _create_job


class TestDedupKeyGeneration:
    """Test 3.2: Verify SHA-256(lowercase(name) + lowercase(city)) produces correct hash"""
    
    def test_dedup_key_basic(self):
        """Test basic dedup key generation"""
        name = "Hotel Himalaya"
        city = "Kathmandu"
        
        expected = hashlib.sha256(b"hotel himalayakathmandu").hexdigest()
        actual = CleaningPipeline._generate_dedup_key(name, city)
        
        assert actual == expected
    
    def test_dedup_key_case_insensitive(self):
        """Test that dedup key is case-insensitive"""
        key1 = CleaningPipeline._generate_dedup_key("Hotel Himalaya", "Kathmandu")
        key2 = CleaningPipeline._generate_dedup_key("HOTEL HIMALAYA", "KATHMANDU")
        key3 = CleaningPipeline._generate_dedup_key("hotel himalaya", "kathmandu")
        
        assert key1 == key2 == key3
    
    def test_dedup_key_with_spaces(self):
        """Test that spaces are preserved in dedup key"""
        name = "Hotel  Himalaya"  # Double space
        city = "Kathmandu"
        
        expected = hashlib.sha256(b"hotel  himalayakathmandu").hexdigest()
        actual = CleaningPipeline._generate_dedup_key(name, city)
        
        assert actual == expected
    
    def test_dedup_key_empty_strings(self):
        """Test dedup key with empty strings"""
        key = CleaningPipeline._generate_dedup_key("", "")
        expected = hashlib.sha256(b"").hexdigest()
        
        assert key == expected
    
    def test_dedup_key_special_characters(self):
        """Test dedup key with special characters"""
        name = "Hôtel Café & Bar"
        city = "Pokhara"
        
        expected = hashlib.sha256("hôtel café & barpokhara".encode()).hexdigest()
        actual = CleaningPipeline._generate_dedup_key(name, city)
        
        assert actual == expected


class TestNormalization:
    """Test 3.3: Test normalization - phone formatting, URL https:// prefix, rating conversion, whitespace stripping"""
    
    def test_whitespace_stripping(self, db_session):
        """Test that whitespace is stripped from all text fields"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "  Hotel Himalaya  ",
            "address": "\n123 Main St\t",
            "city": " Kathmandu ",
            "email": "  info@hotel.com  "
        }
        
        normalized = pipeline._normalize(result)
        
        assert normalized["name"] == "Hotel Himalaya"
        assert normalized["address"] == "123 Main St"
        assert normalized["city"] == "Kathmandu"
        assert normalized["email"] == "info@hotel.com"
    
    def test_phone_formatting(self, db_session):
        """Test phone number formatting - keep only digits and +"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "phone_primary": "+977 (01) 123-4567",
            "phone_secondary": "01-234-5678",
            "whatsapp_number": "+977 98 1234 5678"
        }
        
        normalized = pipeline._normalize(result)
        
        assert normalized["phone_primary"] == "+977011234567"
        assert normalized["phone_secondary"] == "012345678"
        assert normalized["whatsapp_number"] == "+9779812345678"
    
    def test_phone_formatting_with_parentheses(self, db_session):
        """Test phone formatting removes parentheses and dashes"""
        pipeline = CleaningPipeline(db_session)
        
        result = {"phone_primary": "(977) 1-234-5678"}
        normalized = pipeline._normalize(result)
        
        assert normalized["phone_primary"] == "97712345678"
    
    def test_website_https_prefix(self, db_session):
        """Test that website URLs get https:// prefix"""
        pipeline = CleaningPipeline(db_session)
        
        test_cases = [
            ("example.com", "https://example.com"),
            ("www.example.com", "https://www.example.com"),
            ("http://example.com", "https://example.com"),
            ("https://example.com", "https://example.com"),
        ]
        
        for input_url, expected_url in test_cases:
            result = {"website": input_url}
            normalized = pipeline._normalize(result)
            assert normalized["website"] == expected_url, f"Failed for {input_url}"
    
    def test_rating_conversion_from_string(self, db_session):
        """Test rating conversion from "8.5/10" format to float"""
        pipeline = CleaningPipeline(db_session)
        
        test_cases = [
            ("8.5/10", 8.5),
            ("9/10", 9.0),
            ("7.8", 7.8),
            ("10/10", 10.0),
        ]
        
        for input_rating, expected_rating in test_cases:
            result = {"rating_overall": input_rating}
            normalized = pipeline._normalize(result)
            assert normalized["rating_overall"] == expected_rating, f"Failed for {input_rating}"
    
    def test_rating_conversion_all_rating_fields(self, db_session):
        """Test rating conversion works for all rating fields"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "rating_overall": "8.5/10",
            "rating_cleanliness": "9/10",
            "rating_location": "7.5",
            "rating_facilities": "8/10",
            "rating_service": "9.5/10",
            "rating_value": "8.0"
        }
        
        normalized = pipeline._normalize(result)
        
        assert normalized["rating_overall"] == 8.5
        assert normalized["rating_cleanliness"] == 9.0
        assert normalized["rating_location"] == 7.5
        assert normalized["rating_facilities"] == 8.0
        assert normalized["rating_service"] == 9.5
        assert normalized["rating_value"] == 8.0
    
    def test_normalization_preserves_casing(self, db_session):
        """Test that normalization preserves original casing for names and addresses"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "address": "123 Main Street"
        }
        
        normalized = pipeline._normalize(result)
        
        assert normalized["name"] == "Hotel Himalaya"
        assert normalized["address"] == "123 Main Street"
    
    def test_normalization_handles_none_values(self, db_session):
        """Test that normalization handles None values gracefully"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "phone_primary": None,
            "website": None,
            "rating_overall": None
        }
        
        normalized = pipeline._normalize(result)
        
        assert normalized["name"] == "Hotel Himalaya"
        assert normalized["phone_primary"] is None
        assert normalized["website"] is None
        assert normalized["rating_overall"] is None


class TestWithinJobDedup:
    """Test 3.4: Test within-job dedup - duplicates saved with is_duplicate=True for MergingPipeline"""
    
    def test_within_job_dedup_removes_duplicates(self, db_session):
        """Test that duplicates within same job are marked is_duplicate=True, not discarded"""
        pipeline = CleaningPipeline(db_session)
        
        results = [
            {"name": "Hotel Himalaya", "city": "Kathmandu", "phone_primary": "123"},
            {"name": "Hotel Himalaya", "city": "Kathmandu", "phone_primary": "456"},  # Duplicate
            {"name": "Hotel Annapurna", "city": "Pokhara", "phone_primary": "789"},
        ]
        
        deduplicated = pipeline._dedup_within_job(results, "job-123")
        
        # All 3 returned — duplicate saved with is_duplicate=True for MergingPipeline
        assert len(deduplicated) == 3
        assert deduplicated[0]["name"] == "Hotel Himalaya"
        assert deduplicated[0]["phone_primary"] == "123"
        assert deduplicated[0]["is_duplicate"] == False   # canonical
        assert deduplicated[1]["phone_primary"] == "456"
        assert deduplicated[1]["is_duplicate"] == True    # duplicate, but saved
        assert deduplicated[2]["name"] == "Hotel Annapurna"
        assert deduplicated[2]["is_duplicate"] == False
    
    def test_within_job_dedup_keeps_first_occurrence(self, db_session):
        """Test that first occurrence is canonical (is_duplicate=False), subsequent are marked duplicate"""
        pipeline = CleaningPipeline(db_session)
        
        results = [
            {"name": "Hotel A", "city": "City", "data": "first"},
            {"name": "Hotel A", "city": "City", "data": "second"},
            {"name": "Hotel A", "city": "City", "data": "third"},
        ]
        
        deduplicated = pipeline._dedup_within_job(results, "job-123")
        
        # All 3 are returned — duplicates saved with is_duplicate=True for MergingPipeline
        assert len(deduplicated) == 3
        assert deduplicated[0]["data"] == "first"
        assert deduplicated[0]["is_duplicate"] == False
        assert deduplicated[1]["is_duplicate"] == True
        assert deduplicated[2]["is_duplicate"] == True
    
    def test_within_job_dedup_case_insensitive(self, db_session):
        """Test that deduplication is case-insensitive — duplicates saved with is_duplicate=True"""
        pipeline = CleaningPipeline(db_session)
        
        results = [
            {"name": "Hotel Himalaya", "city": "Kathmandu"},
            {"name": "HOTEL HIMALAYA", "city": "KATHMANDU"},  # Same hotel, different case
            {"name": "hotel himalaya", "city": "kathmandu"},  # Same hotel, different case
        ]
        
        deduplicated = pipeline._dedup_within_job(results, "job-123")
        
        # All 3 returned — first is canonical, rest marked is_duplicate=True
        assert len(deduplicated) == 3
        assert deduplicated[0]["is_duplicate"] == False
        assert deduplicated[1]["is_duplicate"] == True
        assert deduplicated[2]["is_duplicate"] == True
    
    def test_within_job_dedup_adds_dedup_key(self, db_session):
        """Test that dedup_key is added to all results"""
        pipeline = CleaningPipeline(db_session)
        
        results = [
            {"name": "Hotel Himalaya", "city": "Kathmandu"},
            {"name": "Hotel Annapurna", "city": "Pokhara"},
        ]
        
        deduplicated = pipeline._dedup_within_job(results, "job-123")
        
        assert "dedup_key" in deduplicated[0]
        assert "dedup_key" in deduplicated[1]
        assert deduplicated[0]["dedup_key"] != deduplicated[1]["dedup_key"]
    
    def test_within_job_dedup_empty_list(self, db_session):
        """Test deduplication with empty list"""
        pipeline = CleaningPipeline(db_session)
        
        deduplicated = pipeline._dedup_within_job([], "job-123")
        
        assert deduplicated == []


class TestCrossJobDedup:
    """Test 3.5: Test cross-job dedup - verify existing records are flagged with is_duplicate=TRUE, still inserted"""
    
    def test_cross_job_dedup_flags_existing_records(self, db_session, create_test_job):
        """Test that existing records are flagged as duplicates"""
        pipeline = CleaningPipeline(db_session)
        
        # Create a job for the existing record
        old_job_id = create_test_job()
        
        # Insert existing record
        dedup_key = CleaningPipeline._generate_dedup_key("Hotel Himalaya", "Kathmandu")
        existing = CleanedResult(
            job_id=old_job_id,
            source_id=1,
            category_id=1,
            dedup_key=dedup_key,
            name="Hotel Himalaya",
            city="Kathmandu",
            status="PENDING"
        )
        db_session.add(existing)
        db_session.commit()
        
        # New results with same dedup_key
        results = [
            {"name": "Hotel Himalaya", "city": "Kathmandu", "dedup_key": dedup_key},
        ]
        
        new_job_id = create_test_job()
        flagged = pipeline._dedup_cross_job(results, category_id=1, job_id=new_job_id)
        
        assert flagged[0]["is_duplicate"] is True
    
    def test_cross_job_dedup_does_not_flag_new_records(self, db_session):
        """Test that new records are not flagged as duplicates"""
        pipeline = CleaningPipeline(db_session)
        
        dedup_key = CleaningPipeline._generate_dedup_key("Hotel New", "Pokhara")
        results = [
            {"name": "Hotel New", "city": "Pokhara", "dedup_key": dedup_key},
        ]
        
        flagged = pipeline._dedup_cross_job(results, category_id=1, job_id=str(uuid.uuid4()))
        
        assert flagged[0]["is_duplicate"] is False
    
    def test_cross_job_dedup_respects_category(self, db_session, create_test_job):
        """Test that cross-job dedup respects category_id"""
        pipeline = CleaningPipeline(db_session)
        
        # Create a job for the existing record
        old_job_id = create_test_job()
        
        # Insert existing record in category 1
        dedup_key = CleaningPipeline._generate_dedup_key("Hotel Himalaya", "Kathmandu")
        existing = CleanedResult(
            job_id=old_job_id,
            source_id=1,
            category_id=1,  # Category 1
            dedup_key=dedup_key,
            name="Hotel Himalaya",
            city="Kathmandu",
            status="PENDING"
        )
        db_session.add(existing)
        db_session.commit()
        
        # New result with same dedup_key but different category
        results = [
            {"name": "Hotel Himalaya", "city": "Kathmandu", "dedup_key": dedup_key},
        ]
        
        # Check against category 2 (different category)
        new_job_id = create_test_job()
        flagged = pipeline._dedup_cross_job(results, category_id=2, job_id=new_job_id)
        
        assert flagged[0]["is_duplicate"] is False  # Not a duplicate in category 2
    
    def test_cross_job_dedup_handles_missing_dedup_key(self, db_session):
        """Test that records without dedup_key are not flagged"""
        pipeline = CleaningPipeline(db_session)
        
        results = [
            {"name": "Hotel", "city": "City"},  # No dedup_key
        ]
        
        flagged = pipeline._dedup_cross_job(results, category_id=1, job_id="job-123")
        
        assert flagged[0]["is_duplicate"] is False


class TestValidation:
    """Test 3.6: Test validation - verify invalid phone/email/rating/lat/lon are set to NULL, record is not rejected"""
    
    def test_validate_phone_must_contain_digits(self, db_session):
        """Test that phone without digits is set to NULL"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "phone_primary": "abc-def-ghij",  # No digits
            "phone_secondary": "+977-123-4567",  # Valid
        }
        
        validated = pipeline._validate(result)
        
        assert validated["phone_primary"] is None
        assert validated["phone_secondary"] == "+977-123-4567"
    
    def test_validate_email_must_contain_at(self, db_session):
        """Test that email without @ is set to NULL"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "email": "invalid.email.com",  # No @
        }
        
        validated = pipeline._validate(result)
        
        assert validated["email"] is None
    
    def test_validate_email_with_at_is_valid(self, db_session):
        """Test that email with @ is kept"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "email": "info@hotel.com",
        }
        
        validated = pipeline._validate(result)
        
        assert validated["email"] == "info@hotel.com"
    
    def test_validate_rating_range_0_to_10(self, db_session):
        """Test that ratings outside 0-10 range are set to NULL"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "rating_overall": 8.5,  # Valid
            "rating_cleanliness": -1.0,  # Invalid (< 0)
            "rating_location": 11.0,  # Invalid (> 10)
            "rating_facilities": 0.0,  # Valid (boundary)
            "rating_service": 10.0,  # Valid (boundary)
        }
        
        validated = pipeline._validate(result)
        
        assert validated["rating_overall"] == 8.5
        assert validated["rating_cleanliness"] is None
        assert validated["rating_location"] is None
        assert validated["rating_facilities"] == 0.0
        assert validated["rating_service"] == 10.0
    
    def test_validate_latitude_range(self, db_session):
        """Test that latitude outside -90 to 90 is set to NULL"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "latitude": 27.7172,  # Valid
        }
        
        validated = pipeline._validate(result)
        assert validated["latitude"] == 27.7172
        
        result = {"latitude": -91.0}  # Invalid
        validated = pipeline._validate(result)
        assert validated["latitude"] is None
        
        result = {"latitude": 91.0}  # Invalid
        validated = pipeline._validate(result)
        assert validated["latitude"] is None
        
        result = {"latitude": -90.0}  # Valid (boundary)
        validated = pipeline._validate(result)
        assert validated["latitude"] == -90.0
        
        result = {"latitude": 90.0}  # Valid (boundary)
        validated = pipeline._validate(result)
        assert validated["latitude"] == 90.0
    
    def test_validate_longitude_range(self, db_session):
        """Test that longitude outside -180 to 180 is set to NULL"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "longitude": 85.3240,  # Valid
        }
        
        validated = pipeline._validate(result)
        assert validated["longitude"] == 85.3240
        
        result = {"longitude": -181.0}  # Invalid
        validated = pipeline._validate(result)
        assert validated["longitude"] is None
        
        result = {"longitude": 181.0}  # Invalid
        validated = pipeline._validate(result)
        assert validated["longitude"] is None
        
        result = {"longitude": -180.0}  # Valid (boundary)
        validated = pipeline._validate(result)
        assert validated["longitude"] == -180.0
        
        result = {"longitude": 180.0}  # Valid (boundary)
        validated = pipeline._validate(result)
        assert validated["longitude"] == 180.0
    
    def test_validate_does_not_reject_record(self, db_session):
        """Test that validation sets invalid fields to NULL but keeps the record"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "phone_primary": "invalid",  # Invalid
            "email": "invalid",  # Invalid
            "rating_overall": 15.0,  # Invalid
            "latitude": 100.0,  # Invalid
            "longitude": 200.0,  # Invalid
        }
        
        validated = pipeline._validate(result)
        
        # Record is not rejected
        assert validated is not None
        assert validated["name"] == "Hotel Himalaya"
        
        # Invalid fields are set to NULL
        assert validated["phone_primary"] is None
        assert validated["email"] is None
        assert validated["rating_overall"] is None
        assert validated["latitude"] is None
        assert validated["longitude"] is None


class TestCompletenessScoring:
    """Test 3.7: Test completeness scoring - verify 14 fields counted correctly, percentage computed correctly"""
    
    def test_completeness_all_fields_present(self, db_session):
        """Test completeness when all 14 key fields are present"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "address": "123 Main St",
            "city": "Kathmandu",
            "phone_primary": "123456",
            "email": "info@hotel.com",
            "website": "https://hotel.com",
            "rating_overall": 8.5,
            "review_count": 100,
            "thumbnail_url": "https://image.com/thumb.jpg",
            "description_short": "A nice hotel",
            "amenities": ["wifi", "parking"],
            "price_min": 5000,
            "latitude": 27.7172,
            "longitude": 85.3240,
        }
        
        scored = pipeline._compute_completeness(result)
        
        assert scored["data_completeness"] == 100.0
    
    def test_completeness_no_fields_present(self, db_session):
        """Test completeness when no key fields are present"""
        pipeline = CleaningPipeline(db_session)
        
        result = {}
        
        scored = pipeline._compute_completeness(result)
        
        assert scored["data_completeness"] == 0.0
    
    def test_completeness_half_fields_present(self, db_session):
        """Test completeness when 7 out of 14 fields are present"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "address": "123 Main St",
            "city": "Kathmandu",
            "phone_primary": "123456",
            "email": "info@hotel.com",
            "website": "https://hotel.com",
            "rating_overall": 8.5,
            # 7 fields missing
        }
        
        scored = pipeline._compute_completeness(result)
        
        assert scored["data_completeness"] == 50.0
    
    def test_completeness_ignores_null_values(self, db_session):
        """Test that NULL values are not counted"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "address": None,
            "city": "Kathmandu",
            "phone_primary": None,
            "email": None,
            "website": None,
            "rating_overall": None,
            "review_count": None,
            "thumbnail_url": None,
            "description_short": None,
            "amenities": None,
            "price_min": None,
            "latitude": None,
            "longitude": None,
        }
        
        scored = pipeline._compute_completeness(result)
        
        # Only 2 fields present: name and city
        expected = (2 / 14) * 100
        assert scored["data_completeness"] == round(expected, 2)
    
    def test_completeness_ignores_empty_strings(self, db_session):
        """Test that empty strings are not counted"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "address": "",  # Empty string
            "city": "   ",  # Whitespace only
            "phone_primary": "123456",
            "email": "",
            "website": "",
            "rating_overall": 8.5,
            "review_count": 100,
            "thumbnail_url": "",
            "description_short": "",
            "amenities": ["wifi"],
            "price_min": 5000,
            "latitude": 27.7172,
            "longitude": 85.3240,
        }
        
        scored = pipeline._compute_completeness(result)
        
        # 8 non-empty fields: name, phone_primary, rating_overall, review_count, amenities, price_min, latitude, longitude
        expected = (8 / 14) * 100
        assert scored["data_completeness"] == round(expected, 2)
    
    def test_completeness_only_counts_14_key_fields(self, db_session):
        """Test that only the 14 key fields are counted, not other fields"""
        pipeline = CleaningPipeline(db_session)
        
        result = {
            "name": "Hotel Himalaya",
            "city": "Kathmandu",
            # Extra fields that should not be counted
            "brand": "Himalaya Hotels",
            "property_type": "Hotel",
            "star_rating": 5,
            "district": "Thamel",
            "province": "Bagmati",
        }
        
        scored = pipeline._compute_completeness(result)
        
        # Only 2 of the 14 key fields are present
        expected = (2 / 14) * 100
        assert scored["data_completeness"] == round(expected, 2)


class TestPipelineIntegration:
    """Integration tests for the full pipeline"""
    
    def test_pipeline_saves_raw_results(self, db_session, create_test_job):
        """Test that raw results are saved to raw_results table"""
        pipeline = CleaningPipeline(db_session)
        
        raw_results = [
            {"name": "Hotel A", "city": "City A"},
            {"name": "Hotel B", "city": "City B"},
        ]
        
        job_id = create_test_job()
        pipeline.process(raw_results, job_id=job_id, source_id=1, category_id=1)
        
        # Check raw_results table
        raw_count = db_session.query(RawResult).filter(RawResult.job_id == job_id).count()
        assert raw_count == 2
    
    def test_pipeline_saves_cleaned_results(self, db_session, create_test_job):
        """Test that cleaned results are saved to cleaned_results table"""
        pipeline = CleaningPipeline(db_session)
        
        raw_results = [
            {
                "name": "Hotel Himalaya",
                "city": "Kathmandu",
                "phone_primary": "+977-123-4567",
                "rating_overall": "8.5/10",
            },
        ]
        
        job_id = create_test_job()
        pipeline.process(raw_results, job_id=job_id, source_id=1, category_id=1)
        
        # Check cleaned_results table
        cleaned = db_session.query(CleanedResult).filter(CleanedResult.job_id == job_id).first()
        
        assert cleaned is not None
        assert cleaned.name == "Hotel Himalaya"
        assert cleaned.city == "Kathmandu"
        assert cleaned.phone_primary == "+9771234567"  # Normalized
        assert cleaned.rating_overall == Decimal("8.5")  # Converted
        assert cleaned.status == "PENDING"
        assert cleaned.is_duplicate is False
    
    def test_pipeline_end_to_end(self, db_session, create_test_job):
        """Test complete pipeline with normalization, dedup, validation, and completeness"""
        pipeline = CleaningPipeline(db_session)
        
        raw_results = [
            {
                "name": "  Hotel Himalaya  ",
                "city": "Kathmandu",
                "phone_primary": "+977 (01) 123-4567",
                "email": "info@hotel.com",
                "website": "hotel.com",
                "rating_overall": "8.5/10",
                "latitude": 27.7172,
                "longitude": 85.3240,
            },
            {
                "name": "Hotel Himalaya",  # Duplicate
                "city": "Kathmandu",
                "phone_primary": "different",
            },
            {
                "name": "Hotel Annapurna",
                "city": "Pokhara",
                "email": "invalid-email",  # Invalid
                "rating_overall": 15.0,  # Invalid
            },
        ]
        
        job_id = create_test_job()
        cleaned = pipeline.process(raw_results, job_id=job_id, source_id=1, category_id=1)
        
        # Should have 3 results (duplicate now saved with is_duplicate=True for MergingPipeline)
        assert len(cleaned) == 3
        
        # First result should be normalized (canonical)
        assert cleaned[0]["name"] == "Hotel Himalaya"
        assert cleaned[0]["phone_primary"] == "+977011234567"
        assert cleaned[0]["website"] == "https://hotel.com"
        assert cleaned[0]["rating_overall"] == 8.5
        assert cleaned[0]["is_duplicate"] == False
        
        # Second result is the within-job duplicate — saved with is_duplicate=True
        assert cleaned[1]["name"] == "Hotel Himalaya"
        assert cleaned[1]["is_duplicate"] == True
        
        # Third result should have invalid fields set to NULL
        assert cleaned[2]["name"] == "Hotel Annapurna"
        assert cleaned[2]["email"] is None
        assert cleaned[2]["rating_overall"] is None
        
        # All should have completeness scores
        assert "data_completeness" in cleaned[0]
        assert "data_completeness" in cleaned[1]
        assert "data_completeness" in cleaned[2]
        
        # Check database — all 3 saved (duplicate saved with is_duplicate=True for MergingPipeline)
        db_results = db_session.query(CleanedResult).filter(CleanedResult.job_id == job_id).all()
        assert len(db_results) == 3
        # Verify the within-job duplicate is flagged
        dup_results = [r for r in db_results if r.is_duplicate]
        assert len(dup_results) >= 1
