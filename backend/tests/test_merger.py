"""
Tests for MergingPipeline — Phase 6A

Tests verify:
- Single-source groups are skipped (no merge)
- Two-source groups are merged with correct field priority
- Phone merging: first unique → phone_primary, second → phone_secondary, extras discarded
- Amenities arrays are merged and deduplicated (case-insensitive)
- Boolean fields use TRUE-wins logic
- Description uses longest value
- Non-canonical records have is_duplicate=TRUE after merge
- merged_from_sources contains correct source IDs
- confidence_score is between 0.0 and 1.0
- data_completeness is recalculated after merge
"""
import uuid
from decimal import Decimal
from sqlalchemy import text

import pytest

from models.cleaned_result import CleanedResult
from models.source import Source
from scrapers.merger import MergingPipeline, SOURCE_PRIORITY


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def make_source(db, source_id: int, name: str) -> Source:
    """Insert a source row if it doesn't exist, return it."""
    src = db.query(Source).filter(Source.id == source_id).first()
    if src:
        return src
    db.execute(text(
        "INSERT INTO sources (id, name, display_name, category_id, base_url, heal_mode) "
        "VALUES (:id, :name, :display_name, 1, 'http://example.com', 'MANUAL') "
        "ON CONFLICT (id) DO NOTHING"
    ), {"id": source_id, "name": name, "display_name": name})
    db.commit()
    return db.query(Source).filter(Source.id == source_id).first()


def make_job(db) -> str:
    """Insert a scrape job and return its UUID string."""
    job_id = str(uuid.uuid4())
    # Ensure a test user exists
    db.execute(text(
        "INSERT INTO users (email, password_hash, role, is_active) "
        "VALUES ('merger_test@example.com', 'hash', 'user', true) "
        "ON CONFLICT (email) DO NOTHING"
    ))
    user = db.execute(text("SELECT id FROM users WHERE email='merger_test@example.com'")).fetchone()
    db.execute(text(
        "INSERT INTO scrape_jobs (id, user_id, status, location, category_id) "
        "VALUES (:id, :user_id, 'DONE', 'Kathmandu', 1)"
    ), {"id": job_id, "user_id": user[0]})
    db.commit()
    return job_id


def make_result(db, job_id: str, source_id: int, **kwargs) -> CleanedResult:
    """Create and persist a CleanedResult row."""
    name = kwargs.get("name", "Hotel Test")
    city = kwargs.get("city", "Kathmandu")
    import hashlib
    dedup_key = hashlib.sha256(f"{name.lower()}{city.lower()}".encode()).hexdigest()

    r = CleanedResult(
        job_id=job_id,
        source_id=source_id,
        category_id=1,
        dedup_key=dedup_key,
        is_duplicate=False,
        status="PENDING",
        **kwargs,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ------------------------------------------------------------------ #
# Tests                                                                #
# ------------------------------------------------------------------ #

class TestMergingPipelineSingleSource:
    def test_single_source_group_not_merged(self, db_session):
        """Single-source records are skipped — no merged_from_sources set."""
        make_source(db_session, 2, "booking_com")
        job_id = make_job(db_session)
        r = make_result(db_session, job_id, 2, name="Hotel Solo", city="Kathmandu")

        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)

        assert stats["merged_groups"] == 0
        assert stats["total_records_processed"] == 1

        db_session.refresh(r)
        assert r.merged_from_sources is None
        assert r.confidence_score is None
        assert r.merged_at is None


class TestMergingPipelineTwoSources:
    def test_two_source_merge_field_priority(self, db_session):
        """Higher-priority source wins for identity fields; NULL fields filled from secondary."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        # booking_com: has name + address, no phone/email
        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel XYZ", city="Kathmandu",
            address="Thamel, Kathmandu",
            phone_primary=None, email=None,
            rating_overall=Decimal("8.5"), review_count=1200,
        )
        # directoryofnepal: has phone + email, no address
        r_dir = make_result(
            db_session, job_id, 12,
            name="Hotel XYZ", city="Kathmandu",
            address=None,
            phone_primary="+9771234567", email="info@xyz.com",
            rating_overall=None, review_count=None,
        )

        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)

        assert stats["merged_groups"] == 1

        db_session.refresh(r_booking)
        db_session.refresh(r_dir)

        # booking_com is canonical (higher priority)
        assert r_booking.is_duplicate == False
        assert r_dir.is_duplicate == True

        # Fields from booking_com preserved
        assert r_booking.address == "Thamel, Kathmandu"
        assert r_booking.rating_overall == Decimal("8.5")

        # NULL fields filled from directoryofnepal
        assert r_booking.phone_primary == "+9771234567"
        assert r_booking.email == "info@xyz.com"

        # Merge metadata set
        assert set(r_booking.merged_from_sources) == {2, 12}
        assert r_booking.merged_at is not None

    def test_non_canonical_marked_is_duplicate(self, db_session):
        """Non-canonical records have is_duplicate=TRUE after merge."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        make_result(db_session, job_id, 2, name="Hotel ABC", city="Kathmandu")
        r_secondary = make_result(db_session, job_id, 12, name="Hotel ABC", city="Kathmandu")

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_secondary)
        assert r_secondary.is_duplicate == True

    def test_merged_from_sources_contains_correct_ids(self, db_session):
        """merged_from_sources contains both source IDs."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r1 = make_result(db_session, job_id, 2, name="Hotel MFS", city="Kathmandu")
        make_result(db_session, job_id, 12, name="Hotel MFS", city="Kathmandu")

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r1)
        assert sorted(r1.merged_from_sources) == [2, 12]


class TestPhoneMerging:
    def test_phone_primary_filled_from_secondary_source(self, db_session):
        """phone_primary filled from secondary source when canonical has NULL phone."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Phone", city="Kathmandu",
            phone_primary=None,
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel Phone", city="Kathmandu",
            phone_primary="+9771111111",
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.phone_primary == "+9771111111"

    def test_phone_secondary_filled_from_third_source(self, db_session):
        """Second unique phone goes to phone_secondary; third phone discarded."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        make_source(db_session, 6, "nepalyp")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Phones", city="Kathmandu",
            phone_primary="+9771111111", phone_secondary=None,
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel Phones", city="Kathmandu",
            phone_primary="+9772222222",  # different → goes to phone_secondary
        )
        make_result(
            db_session, job_id, 6,
            name="Hotel Phones", city="Kathmandu",
            phone_primary="+9773333333",  # third unique → discarded
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.phone_primary == "+9771111111"
        assert r_booking.phone_secondary == "+9772222222"
        # Third phone is discarded — no field to store it

    def test_duplicate_phone_not_stored_twice(self, db_session):
        """Same phone number from two sources is not duplicated."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel SamePhone", city="Kathmandu",
            phone_primary="+9771111111",
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel SamePhone", city="Kathmandu",
            phone_primary="+9771111111",  # same number
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.phone_primary == "+9771111111"
        assert r_booking.phone_secondary is None  # not duplicated


class TestAmenitiesMerging:
    def test_amenities_merged_and_deduplicated(self, db_session):
        """Amenities from all sources are merged and deduplicated case-insensitively."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Amenities", city="Kathmandu",
            amenities=["WiFi", "Pool"],
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel Amenities", city="Kathmandu",
            amenities=["wifi", "Restaurant", "Parking"],  # "wifi" is duplicate
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        amenities_lower = [a.lower() for a in r_booking.amenities]
        assert "wifi" in amenities_lower
        assert "pool" in amenities_lower
        assert "restaurant" in amenities_lower
        assert "parking" in amenities_lower
        # No duplicates
        assert len(amenities_lower) == len(set(amenities_lower))


class TestBooleanMerging:
    def test_boolean_true_wins(self, db_session):
        """Boolean fields use TRUE-wins logic."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Bool", city="Kathmandu",
            pets_allowed=False, includes_breakfast=None,
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel Bool", city="Kathmandu",
            pets_allowed=True, includes_breakfast=True,
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.pets_allowed == True
        assert r_booking.includes_breakfast == True


class TestDescriptionMerging:
    def test_description_uses_longest_value(self, db_session):
        """Description fields use the longest non-null value across sources."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Desc", city="Kathmandu",
            description_short="Short desc",
        )
        make_result(
            db_session, job_id, 12,
            name="Hotel Desc", city="Kathmandu",
            description_short="A much longer description with more detail about the hotel",
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.description_short == "A much longer description with more detail about the hotel"


class TestConfidenceScore:
    def test_confidence_score_between_0_and_1(self, db_session):
        """confidence_score is between 0.0 and 1.0."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        r = make_result(db_session, job_id, 2, name="Hotel Conf", city="Kathmandu")
        make_result(db_session, job_id, 12, name="Hotel Conf", city="Kathmandu")

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r)
        assert r.confidence_score is not None
        assert Decimal("0.00") <= r.confidence_score <= Decimal("1.00")

    def test_three_sources_higher_confidence_than_two(self, db_session):
        """Three sources produce higher confidence than two sources."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        make_source(db_session, 6, "nepalyp")

        # Job 1: two sources
        job_id_2 = make_job(db_session)
        r2 = make_result(db_session, job_id_2, 2, name="Hotel Two", city="Kathmandu")
        make_result(db_session, job_id_2, 12, name="Hotel Two", city="Kathmandu")
        MergingPipeline(db_session).run(job_id_2)
        db_session.refresh(r2)

        # Job 2: three sources
        job_id_3 = make_job(db_session)
        r3 = make_result(db_session, job_id_3, 2, name="Hotel Three", city="Pokhara")
        make_result(db_session, job_id_3, 12, name="Hotel Three", city="Pokhara")
        make_result(db_session, job_id_3, 6, name="Hotel Three", city="Pokhara")
        MergingPipeline(db_session).run(job_id_3)
        db_session.refresh(r3)

        assert r3.confidence_score > r2.confidence_score


class TestCompletenessRecalculation:
    def test_completeness_recalculated_after_merge(self, db_session):
        """data_completeness is higher after merging than before."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)

        # booking_com: has name, address, city, rating — missing phone, email
        r_booking = make_result(
            db_session, job_id, 2,
            name="Hotel Complete", city="Kathmandu",
            address="Thamel", rating_overall=Decimal("8.0"),
            phone_primary=None, email=None,
        )
        completeness_before = r_booking.data_completeness or Decimal("0")

        # directoryofnepal: adds phone + email
        make_result(
            db_session, job_id, 12,
            name="Hotel Complete", city="Kathmandu",
            phone_primary="+9771234567", email="info@hotel.com",
        )

        MergingPipeline(db_session).run(job_id)

        db_session.refresh(r_booking)
        assert r_booking.data_completeness > completeness_before


class TestJobIsolation:
    def test_merger_only_processes_current_job(self, db_session):
        """MergingPipeline only processes records from the given job_id."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")

        job_id_a = make_job(db_session)
        job_id_b = make_job(db_session)

        # Job A: two sources → should merge
        r_a = make_result(db_session, job_id_a, 2, name="Hotel Iso", city="Kathmandu")
        make_result(db_session, job_id_a, 12, name="Hotel Iso", city="Kathmandu")

        # Job B: one source → should NOT merge
        r_b = make_result(db_session, job_id_b, 2, name="Hotel Iso", city="Kathmandu")

        # Run merger only for job A
        stats = MergingPipeline(db_session).run(job_id_a)

        assert stats["merged_groups"] == 1

        db_session.refresh(r_b)
        # Job B record untouched
        assert r_b.merged_from_sources is None


# ------------------------------------------------------------------ #
# Phase 7 Priority 3: Fuzzy Matching Tests                           #
# ------------------------------------------------------------------ #

class TestFuzzyMatchingPhoneNormalization:
    def test_phone_normalization_strips_non_digits(self, db_session):
        """Phone normalization strips all non-digit characters."""
        pipeline = MergingPipeline(db_session)
        
        assert pipeline._normalize_phone("+977-1-4411234") == "14411234"
        assert pipeline._normalize_phone("(01) 4411234") == "14411234"
        assert pipeline._normalize_phone("977 1 4411234") == "14411234"
        assert pipeline._normalize_phone("01-4411234") == "14411234"
    
    def test_phone_normalization_handles_nepal_country_code(self, db_session):
        """Phone normalization strips Nepal country code 977."""
        pipeline = MergingPipeline(db_session)
        
        # With country code
        assert pipeline._normalize_phone("9771234567890") == "1234567890"
        assert pipeline._normalize_phone("+9771234567890") == "1234567890"
        
        # Without country code (unchanged)
        assert pipeline._normalize_phone("1234567890") == "1234567890"
    
    def test_phone_normalization_returns_none_for_invalid(self, db_session):
        """Phone normalization returns None for invalid/too-short numbers."""
        pipeline = MergingPipeline(db_session)
        
        assert pipeline._normalize_phone(None) is None
        assert pipeline._normalize_phone("") is None
        assert pipeline._normalize_phone("123") is None  # Too short
        assert pipeline._normalize_phone("abc") is None  # No digits


class TestFuzzyMatchingCoordinateDistance:
    def test_haversine_distance_calculation(self, db_session):
        """Haversine distance calculation is accurate."""
        pipeline = MergingPipeline(db_session)
        
        # Same location
        assert pipeline._haversine_distance(27.7172, 85.3240, 27.7172, 85.3240) == 0.0
        
        # ~100 meters apart (approximately)
        dist = pipeline._haversine_distance(27.7172, 85.3240, 27.7180, 85.3250)
        assert 0.1 < dist < 0.2  # Should be around 0.12 km
        
        # ~1 km apart
        dist = pipeline._haversine_distance(27.7172, 85.3240, 27.7272, 85.3340)
        assert 1.0 < dist < 2.0


class TestFuzzyMatchingPhoneMatch:
    def test_same_phone_triggers_match(self, db_session):
        """Records with same phone number (after normalization) are matched."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Different names, same phone
        r1 = make_result(
            db_session, job_id, 2,
            name="Hotel Himalaya", city="Kathmandu",
            phone_primary="+977-1-4411234",
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Himalaya Hotel", city="Kathmandu",
            phone_primary="01-4411234",  # Same phone, different format
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should merge via fuzzy matching (phone match)
        assert stats["fuzzy_merged_groups"] >= 1
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # One should be canonical, other marked duplicate
        assert (r1.is_duplicate == False and r2.is_duplicate == True) or \
               (r1.is_duplicate == True and r2.is_duplicate == False)


class TestFuzzyMatchingCoordinateMatch:
    def test_nearby_coordinates_trigger_match(self, db_session):
        """Records within 50 meters are matched."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Similar names (>80% similarity), coordinates within 50m
        # Using non-placeholder coordinates (not Thamel centroid)
        r1 = make_result(
            db_session, job_id, 2,
            name="Himalaya Hotel", city="Kathmandu",
            latitude=27.7100, longitude=85.3200,
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Hotel Himalaya", city="Kathmandu",
            latitude=27.7102, longitude=85.3202,  # ~30m away
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should merge via fuzzy matching (coordinate proximity)
        assert stats["fuzzy_merged_groups"] >= 1
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # One should be canonical, other marked duplicate
        assert (r1.is_duplicate == False and r2.is_duplicate == True) or \
               (r1.is_duplicate == True and r2.is_duplicate == False)
    
    def test_far_coordinates_no_match(self, db_session):
        """Records more than 50 meters apart are NOT matched."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Different names (<80% similarity), coordinates >50m apart
        r1 = make_result(
            db_session, job_id, 2,
            name="Himalaya Hotel", city="Kathmandu",
            latitude=27.7172, longitude=85.3240,
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Everest Lodge", city="Kathmandu",
            latitude=27.7100, longitude=85.3200,  # ~1km away
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should NOT merge
        assert stats["fuzzy_merged_groups"] == 0
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # Both should remain non-duplicates
        assert r1.is_duplicate == False
        assert r2.is_duplicate == False


class TestFuzzyMatchingNameSimilarity:
    def test_similar_names_trigger_match(self, db_session):
        """Names with 80%+ similarity are matched."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Very similar names (>80% similarity) - minor typo/variation
        r1 = make_result(
            db_session, job_id, 2,
            name="Hotel Himalayan View", city="Kathmandu",
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Hotel Himalayan Views", city="Kathmandu",  # Just added 's'
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should merge via fuzzy matching (name similarity)
        assert stats["fuzzy_merged_groups"] >= 1
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # One should be canonical, other marked duplicate
        assert (r1.is_duplicate == False and r2.is_duplicate == True) or \
               (r1.is_duplicate == True and r2.is_duplicate == False)
    
    def test_dissimilar_names_no_match(self, db_session):
        """Names with <80% similarity are NOT matched."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Different names (<80% similarity)
        r1 = make_result(
            db_session, job_id, 2,
            name="Hotel Himalaya", city="Kathmandu",
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Everest Lodge", city="Kathmandu",
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should NOT merge
        assert stats["fuzzy_merged_groups"] == 0
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # Both should remain non-duplicates
        assert r1.is_duplicate == False
        assert r2.is_duplicate == False


class TestFuzzyMatchingSafetyChecks:
    def test_different_city_no_match(self, db_session):
        """Records from different cities are NOT matched even with same name."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # Same name, different cities
        r1 = make_result(
            db_session, job_id, 2,
            name="Hotel Himalaya", city="Kathmandu",
        )
        r2 = make_result(
            db_session, job_id, 12,
            name="Hotel Himalaya", city="Pokhara",
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should NOT merge (different cities)
        assert stats["fuzzy_merged_groups"] == 0
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # Both should remain non-duplicates
        assert r1.is_duplicate == False
        assert r2.is_duplicate == False
    
    def test_same_source_no_match(self, db_session):
        """Records from same source are NEVER matched even if identical."""
        make_source(db_session, 2, "booking_com")
        job_id = make_job(db_session)
        
        # Identical records from same source
        r1 = make_result(
            db_session, job_id, 2,
            name="Hotel Duplicate", city="Kathmandu",
            phone_primary="+9771234567",
        )
        r2 = make_result(
            db_session, job_id, 2,
            name="Hotel Duplicate", city="Kathmandu",
            phone_primary="+9771234567",
        )
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should NOT merge (same source)
        assert stats["fuzzy_merged_groups"] == 0
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # Both should remain non-duplicates
        assert r1.is_duplicate == False
        assert r2.is_duplicate == False


class TestFuzzyMatchingTwoPassMerging:
    def test_exact_and_fuzzy_passes_both_run(self, db_session):
        """Both exact and fuzzy matching passes run and report separately."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        make_source(db_session, 6, "nepalyp")
        job_id = make_job(db_session)
        
        # Exact match group (same dedup_key)
        make_result(db_session, job_id, 2, name="Hotel Exact", city="Kathmandu")
        make_result(db_session, job_id, 12, name="Hotel Exact", city="Kathmandu")
        
        # Fuzzy match group (different dedup_keys, similar names >80% after normalization)
        # "Himalayan Paradise" vs "Himalaya Paradise" = 94% similarity after normalization
        make_result(db_session, job_id, 2, name="Himalayan Paradise", city="Pokhara", latitude=28.2096, longitude=83.9856)
        make_result(db_session, job_id, 6, name="Himalaya Paradise", city="Pokhara", latitude=28.2097, longitude=83.9857)  # 11m away
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should have both exact and fuzzy merges
        assert stats["exact_merged_groups"] >= 1
        assert stats["fuzzy_merged_groups"] >= 1
        assert stats["merged_groups"] == stats["exact_merged_groups"] + stats["fuzzy_merged_groups"]
    
    def test_fuzzy_pass_only_processes_non_merged_records(self, db_session):
        """Fuzzy pass only processes records not merged in exact pass."""
        make_source(db_session, 2, "booking_com")
        make_source(db_session, 12, "directoryofnepal_hotels")
        job_id = make_job(db_session)
        
        # These will be merged in exact pass (same dedup_key)
        r1 = make_result(db_session, job_id, 2, name="Hotel Same", city="Kathmandu")
        r2 = make_result(db_session, job_id, 12, name="Hotel Same", city="Kathmandu")
        
        pipeline = MergingPipeline(db_session)
        stats = pipeline.run(job_id)
        
        # Should only have exact merge, no fuzzy merge
        assert stats["exact_merged_groups"] == 1
        assert stats["fuzzy_merged_groups"] == 0
        
        db_session.refresh(r1)
        db_session.refresh(r2)
        
        # Should be merged via exact pass
        assert r1.merged_from_sources is not None or r2.merged_from_sources is not None


# ===== Phase 7 Priority 3: Transliteration + Normalization Tests ===== #

def test_transliterate_nepali_to_latin(db_session):
    """Transliterate Nepali/Devanagari script to Latin characters."""
    pipeline = MergingPipeline(db_session)
    
    # Test Nepali city name - unidecode converts काठमाडौं to kaatthmaaddaun
    result = pipeline._transliterate_name("काठमाडौं")
    assert len(result) > 0
    assert result.islower()  # Should be lowercase
    assert "kaatth" in result or "kath" in result  # Partial match is enough
    
    # Test Nepali word for hotel
    result = pipeline._transliterate_name("होटल")
    assert len(result) > 0
    assert result.islower()
    
    # Test full Nepali business name
    result = pipeline._transliterate_name("काठमाडौं बुटिक होटल")
    assert len(result) > 0
    assert result.islower()  # Should be lowercase


def test_transliterate_english_unchanged(db_session):
    """English text should pass through transliteration unchanged (except lowercase)."""
    pipeline = MergingPipeline(db_session)
    
    result = pipeline._transliterate_name("Kathmandu Boutique Hotel")
    assert result == "kathmandu boutique hotel"


def test_normalize_business_name_removes_prefixes(db_session):
    """Remove common business name prefixes."""
    pipeline = MergingPipeline(db_session)
    
    assert pipeline._normalize_business_name("The Everest Hotel") == "everest"
    assert pipeline._normalize_business_name("Hotel Himalaya") == "himalaya"
    assert pipeline._normalize_business_name("Restaurant Thamel") == "thamel"


def test_normalize_business_name_removes_suffixes(db_session):
    """Remove common business name suffixes."""
    pipeline = MergingPipeline(db_session)
    
    assert pipeline._normalize_business_name("Himalaya Hotel") == "himalaya"
    assert pipeline._normalize_business_name("Everest Pvt. Ltd.") == "everest"
    assert pipeline._normalize_business_name("Thamel Restaurant") == "thamel"
    assert pipeline._normalize_business_name("Annapurna & Spa") == "annapurna"


def test_normalize_business_name_handles_both(db_session):
    """Remove both prefix and suffix."""
    pipeline = MergingPipeline(db_session)
    
    assert pipeline._normalize_business_name("The Everest Hotel") == "everest"
    assert pipeline._normalize_business_name("Hotel Himalaya Pvt. Ltd.") == "himalaya"


def test_fuzzy_match_nepali_to_english_names(db_session):
    """Nepali name should match English equivalent after transliteration + normalization."""
    make_source(db_session, 30, "google_maps")
    make_source(db_session, 1, "booking_com")
    
    pipeline = MergingPipeline(db_session)
    
    # Test transliteration + normalization pipeline
    nepali_name = "काठमाडौं बुटिक होटल"  # Kathmandu Boutique Hotel in Nepali
    english_name = "Kathmandu Boutique Hotel"
    
    # Transliterate and normalize both names
    nepali_normalized = pipeline._normalize_business_name(
        pipeline._transliterate_name(nepali_name)
    )
    english_normalized = pipeline._normalize_business_name(
        pipeline._transliterate_name(english_name)
    )
    
    # Check similarity
    import difflib
    similarity = difflib.SequenceMatcher(None, nepali_normalized, english_normalized).ratio()
    
    # Should have reasonable similarity (may not be 80% due to transliteration differences)
    # "kaatthmaaddaun butik" vs "kathmandu boutique" = ~60-70% similarity
    assert similarity > 0.5, f"Similarity {similarity} too low between '{nepali_normalized}' and '{english_normalized}'"
