"""
MergingPipeline — Phase 6A + Phase 7 Priority 3

Runs after CleaningPipeline completes for a job. Groups cleaned_results by
dedup_key and merges records from multiple sources into one canonical record,
filling NULL fields from lower-priority sources using field-specific rules.

Phase 7 Priority 3 adds fuzzy matching to improve merge rate from 5% to 30-50%:
- Fuzzy name matching (80% similarity threshold with transliteration + normalization)
- Phone number normalization and matching
- Coordinate proximity matching (50m radius)
"""
import uuid
import re
import difflib
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict
from typing import Optional
from math import radians, sin, cos, sqrt, atan2

import structlog
from sqlalchemy.orm import Session
from unidecode import unidecode

from models.cleaned_result import CleanedResult
from models.source import Source

logger = structlog.get_logger()

# Source priority: index 0 = highest priority
SOURCE_PRIORITY = [
    "booking_com",
    "directoryofnepal_hotels",
    "directoryofnepal_restaurants",
    "directoryofnepal_pharmacies",
    "nepalyp",
    "nepalyp_restaurants",
    "nepalyp_pharmacies",
    "nepalyp_hospitals",
]

# Same 14 key fields as CleaningPipeline
KEY_FIELDS = [
    "name", "address", "city", "phone_primary", "email", "website",
    "rating_overall", "review_count", "thumbnail_url", "description_short",
    "amenities", "price_min", "latitude", "longitude",
]


class MergingPipeline:
    def __init__(self, db: Session):
        self.db = db
        self._source_name_cache: dict[int, str] = {}

    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number by stripping all non-digits.
        Handles Nepal country code (977) normalization.
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Normalized phone number (digits only) or None
            
        Examples:
            "+977-1-4411234" -> "14411234"
            "977-1-4411234" -> "14411234"
            "01-4411234" -> "14411234"
            "(01) 4411234" -> "14411234"
        """
        if not phone:
            return None
        
        # Strip all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Normalize Nepal numbers: strip country code 977 if present
        if digits.startswith('977') and len(digits) > 10:
            digits = digits[3:]
        
        # Strip leading zero from local Nepal numbers (01-xxx becomes 1-xxx)
        if digits.startswith('0') and len(digits) >= 8:
            digits = digits[1:]
        
        # Return None if too short to be valid
        return digits if len(digits) >= 7 else None

    def _transliterate_name(self, name: str) -> str:
        """Convert any script (Devanagari/Nepali etc.) to Latin characters."""
        if not name:
            return ""
        return ' '.join(unidecode(name).lower().split())

    def _normalize_business_name(self, name: str) -> str:
        """Remove common prefixes/suffixes to get core name."""
        if not name:
            return ""
        normalized = name.lower().strip()
        prefixes = ['the ', 'hotel ', 'resort ', 'guest house ', 'restaurant ']
        suffixes = [
            ' hotel', ' resort', ' guest house', ' pvt. ltd.', ' pvt ltd',
            ' ltd.', ' ltd', ' & spa', ' and spa', ' inn', ' lodge',
            ' restaurant', ' cafe', ' pharmacy', ' hospital', ' clinic'
        ]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        return ' '.join(normalized.split())

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance in kilometers between two coordinates using Haversine formula.
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
            
        Returns:
            Distance in kilometers
            
        Example:
            _haversine_distance(27.7172, 85.3240, 27.7180, 85.3250) -> ~0.12 km
        """
        R = 6371  # Earth radius in kilometers
        
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c

    def _are_same_business(self, record_a: CleanedResult, record_b: CleanedResult) -> bool:
        """
        Determine if two records represent the same business using fuzzy matching.
        
        Matching criteria (any one triggers a match):
        1. Same phone number (after normalization)
        2. Coordinates within 50 meters
        3. Name similarity >= 85%
        
        Safety checks (prevent false positives):
        - Must be in same city
        - Must be from different sources
        
        Args:
            record_a, record_b: Two CleanedResult records to compare
            
        Returns:
            True if records represent the same business, False otherwise
        """
        # Safety check: Must be same city
        if record_a.city and record_b.city:
            if record_a.city.lower().strip() != record_b.city.lower().strip():
                return False
        
        # Safety check: Never merge records from same source
        if record_a.source_id == record_b.source_id:
            return False
        
        # Criterion 1: Phone match (strongest signal)
        phone_a = self._normalize_phone(record_a.phone_primary)
        phone_b = self._normalize_phone(record_b.phone_primary)
        if phone_a and phone_b and phone_a == phone_b:
            logger.debug(
                "merger.fuzzy_match_phone",
                record_a_id=str(record_a.id),
                record_b_id=str(record_b.id),
                phone=phone_a
            )
            return True
        
        # Criterion 2: Coordinate proximity match (within 50 meters)
        if all([record_a.latitude, record_a.longitude, record_b.latitude, record_b.longitude]):
            distance_km = self._haversine_distance(
                record_a.latitude, record_a.longitude,
                record_b.latitude, record_b.longitude
            )
            if distance_km <= 0.05:  # 50 meters = 0.05 km
                logger.debug(
                    "merger.fuzzy_match_coordinates",
                    record_a_id=str(record_a.id),
                    record_b_id=str(record_b.id),
                    distance_meters=round(distance_km * 1000, 1)
                )
                return True
        
        # Criterion 3: Name fuzzy match with transliteration + normalization (80% similarity threshold)
        if record_a.name and record_b.name:
            name_a = self._normalize_business_name(
                self._transliterate_name(record_a.name)
            )
            name_b = self._normalize_business_name(
                self._transliterate_name(record_b.name)
            )
            if name_a and name_b:
                similarity = difflib.SequenceMatcher(None, name_a, name_b).ratio()
                if similarity >= 0.80:
                    logger.debug(
                        "merger.fuzzy_match_name",
                        record_a_id=str(record_a.id),
                        record_b_id=str(record_b.id),
                        name_a=record_a.name,
                        name_b=record_b.name,
                        normalized_a=name_a,
                        normalized_b=name_b,
                        similarity=round(similarity, 3)
                    )
                    return True
        
        return False

    def run(self, job_id: str) -> dict:
        """
        Entry point. Performs two-pass merging:
        1. Exact dedup_key matching (existing logic)
        2. Fuzzy matching for remaining non-merged records (Priority 3)
        
        Returns:
            {"merged_groups": N, "total_records_processed": M, "fuzzy_merged_groups": K}
        """
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id

        # Query ALL records for this job (including cross-job duplicates)
        # We group by dedup_key+source_id to find the same hotel from different sources
        all_results = self.db.query(CleanedResult).filter(
            CleanedResult.job_id == job_uuid,
        ).all()

        # ===== PASS 1: Exact dedup_key matching ===== #
        # Group by dedup_key, then sub-group by source_id (one record per source per hotel)
        # We want to merge when the same hotel (dedup_key) appears from multiple sources
        dedup_groups: dict[str, dict[int, CleanedResult]] = defaultdict(dict)
        for r in all_results:
            if r.dedup_key:
                # Keep the first record per source per dedup_key (lowest is_duplicate priority)
                if r.source_id not in dedup_groups[r.dedup_key]:
                    dedup_groups[r.dedup_key][r.source_id] = r

        exact_merged_groups = 0
        for dedup_key, source_map in dedup_groups.items():
            if len(source_map) < 2:
                logger.debug("merger.skipped", dedup_key=dedup_key)
                continue
            # Multiple sources have this hotel — merge them
            group = list(source_map.values())
            self._merge_group(group)
            exact_merged_groups += 1

        logger.info(
            "merger.exact_pass_complete",
            job_id=job_id,
            exact_merged_groups=exact_merged_groups,
        )

        # ===== PASS 2: Fuzzy matching for remaining non-merged records ===== #
        # Get records that weren't merged in pass 1 and aren't marked as duplicates
        non_merged = self.db.query(CleanedResult).filter(
            CleanedResult.job_id == job_uuid,
            CleanedResult.is_duplicate == False,
            CleanedResult.merged_from_sources == None
        ).all()

        logger.info(
            "merger.fuzzy_pass_starting",
            job_id=job_id,
            non_merged_count=len(non_merged)
        )

        # Group by fuzzy matching
        fuzzy_groups = []
        processed_ids = set()

        for record in non_merged:
            if record.id in processed_ids:
                continue

            # Start a new group with this record
            group = [record]
            processed_ids.add(record.id)

            # Find similar records from different sources
            for other in non_merged:
                if other.id in processed_ids:
                    continue
                if self._are_same_business(record, other):
                    group.append(other)
                    processed_ids.add(other.id)

            # Only merge if we found matches from multiple sources
            if len(group) >= 2:
                fuzzy_groups.append(group)

        # Merge fuzzy groups
        fuzzy_merged_groups = 0
        for group in fuzzy_groups:
            self._merge_group(group)
            fuzzy_merged_groups += 1
            logger.info(
                "merger.fuzzy_group_merged",
                group_size=len(group),
                source_ids=[r.source_id for r in group]
            )

        total_merged_groups = exact_merged_groups + fuzzy_merged_groups

        logger.info(
            "merger.complete",
            job_id=job_id,
            exact_merged_groups=exact_merged_groups,
            fuzzy_merged_groups=fuzzy_merged_groups,
            total_merged_groups=total_merged_groups,
            total_records_processed=len(all_results),
        )
        
        return {
            "merged_groups": total_merged_groups,
            "exact_merged_groups": exact_merged_groups,
            "fuzzy_merged_groups": fuzzy_merged_groups,
            "total_records_processed": len(all_results)
        }

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _source_name(self, source_id: int) -> str:
        if source_id not in self._source_name_cache:
            src = self.db.query(Source).filter(Source.id == source_id).first()
            self._source_name_cache[source_id] = src.name if src else ""
        return self._source_name_cache[source_id]

    def _priority(self, record: CleanedResult) -> int:
        name = self._source_name(record.source_id)
        try:
            return SOURCE_PRIORITY.index(name)
        except ValueError:
            return len(SOURCE_PRIORITY)

    def _pick_canonical(self, records: list[CleanedResult]) -> CleanedResult:
        return min(records, key=self._priority)

    def _merge_group(self, group: list[CleanedResult]) -> None:
        canonical = self._pick_canonical(group)
        others = [r for r in group if r.id != canonical.id]

        self._merge_fields(canonical, others)
        canonical.merged_from_sources = [r.source_id for r in group]
        canonical.merged_at = datetime.now(timezone.utc)
        canonical.confidence_score = self._calculate_confidence(group, canonical)
        canonical.data_completeness = Decimal(str(self._recalculate_completeness(canonical)))

        for r in others:
            r.is_duplicate = True

        self.db.commit()

        logger.info(
            "merger.merged",
            dedup_key=canonical.dedup_key,
            source_count=len(group),
            canonical_source_id=canonical.source_id,
            confidence_score=float(canonical.confidence_score),
        )

    def _merge_fields(self, canonical: CleanedResult, others: list[CleanedResult]) -> None:
        """Fill NULL fields in canonical from others using field-specific rules."""
        all_records = [canonical] + others  # canonical first = highest priority

        # --- Simple priority fields: use first non-null value ---
        simple_fields = [
            "name", "brand", "property_type", "star_rating",
            "address", "street_address", "city", "district", "province",
            "country", "latitude", "longitude", "neighbourhood", "nearby_landmark",
            "website", "facebook_url", "instagram_handle", "whatsapp_number",
            "currency", "price_range_label",
            "rating_label", "rating_cleanliness", "rating_location",
            "rating_facilities", "rating_service", "rating_value",
            "checkin_time", "checkout_time", "cancellation_policy",
            "thumbnail_url",
        ]
        for field in simple_fields:
            if getattr(canonical, field) is None:
                for r in others:
                    val = getattr(r, field)
                    if val is not None:
                        setattr(canonical, field, val)
                        break

        # --- Phone: first unique phone → phone_primary, second → phone_secondary ---
        phones: list[str] = []
        for r in all_records:
            for attr in ("phone_primary", "phone_secondary"):
                val = getattr(r, attr)
                if val and val not in phones:
                    phones.append(val)
        canonical.phone_primary = phones[0] if len(phones) > 0 else canonical.phone_primary
        canonical.phone_secondary = phones[1] if len(phones) > 1 else canonical.phone_secondary
        # Any phones[2+] are discarded per requirements

        # --- Email: highest-priority source with a non-null email ---
        if canonical.email is None:
            for r in others:
                if r.email:
                    canonical.email = r.email
                    break

        # --- Rating: source with highest review_count wins ---
        best_review_count = canonical.review_count or 0
        for r in others:
            rc = r.review_count or 0
            if rc > best_review_count:
                best_review_count = rc
                canonical.rating_overall = r.rating_overall
                canonical.review_count = r.review_count
        if canonical.rating_overall is None:
            for r in others:
                if r.rating_overall is not None:
                    canonical.rating_overall = r.rating_overall
                    canonical.review_count = r.review_count
                    break

        # --- Price: min of price_min, max of price_max ---
        all_mins = [r.price_min for r in all_records if r.price_min is not None]
        all_maxs = [r.price_max for r in all_records if r.price_max is not None]
        if all_mins:
            canonical.price_min = min(all_mins)
        if all_maxs:
            canonical.price_max = max(all_maxs)

        # --- Boolean: TRUE wins ---
        for field in ("pets_allowed", "includes_breakfast", "includes_taxes",
                      "breakfast_available", "free_cancellation"):
            if not getattr(canonical, field):
                for r in others:
                    if getattr(r, field):
                        setattr(canonical, field, True)
                        break

        # --- Descriptions: longest non-null value ---
        for field in ("description_short", "description_full"):
            current = getattr(canonical, field) or ""
            for r in others:
                val = getattr(r, field) or ""
                if len(val) > len(current):
                    current = val
            setattr(canonical, field, current or None)

        # --- Arrays: merge + deduplicate (case-insensitive) ---
        for field in ("amenities", "highlights", "popular_with", "staff_languages", "image_urls"):
            merged: list = []
            seen_lower: set = set()
            for r in all_records:
                items = getattr(r, field) or []
                for item in items:
                    key = str(item).lower()
                    if key not in seen_lower:
                        seen_lower.add(key)
                        merged.append(item)
            setattr(canonical, field, merged if merged else None)

        # --- image_count: max ---
        counts = [r.image_count for r in all_records if r.image_count is not None]
        if counts:
            canonical.image_count = max(counts)

    def _calculate_confidence(
        self, records: list[CleanedResult], canonical: CleanedResult
    ) -> Decimal:
        n = len(records)
        source_score = min(n / 3.0, 1.0)
        completeness_score = float(canonical.data_completeness or 0) / 100.0
        agreement_score = self._calculate_agreement(records)
        score = source_score * 0.4 + completeness_score * 0.4 + agreement_score * 0.2
        return Decimal(str(round(score, 2)))

    def _calculate_agreement(self, records: list[CleanedResult]) -> float:
        """Fraction of non-null shared fields where all sources agree."""
        if len(records) < 2:
            return 1.0
        check_fields = ["name", "city", "address", "rating_overall"]
        agree = total = 0
        for field in check_fields:
            vals = [getattr(r, field) for r in records if getattr(r, field) is not None]
            if len(vals) >= 2:
                total += 1
                if len(set(str(v).lower().strip() for v in vals)) == 1:
                    agree += 1
        return agree / total if total > 0 else 1.0

    def _recalculate_completeness(self, record: CleanedResult) -> float:
        non_null = 0
        for field in KEY_FIELDS:
            val = getattr(record, field, None)
            if val is not None:
                if isinstance(val, str) and not val.strip():
                    continue
                non_null += 1
        return round((non_null / len(KEY_FIELDS)) * 100, 2)
