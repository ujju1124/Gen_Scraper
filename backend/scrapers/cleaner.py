"""
Cleaning Pipeline for Web Scraping Portal Phase 2

This module implements the 7-step cleaning pipeline that processes raw scraper results:
1. Save raw results to raw_results table
2. Normalize data (whitespace, phone format, URL format, rating conversion)
3. Deduplicate within job (same batch)
4. Deduplicate cross-job (against existing records)
5. Validate fields (set invalid to NULL, don't reject)
6. Compute completeness score (14 key fields)
7. Save to cleaned_results table
"""

import hashlib
import re
from typing import Any
from decimal import Decimal
from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from models.raw_result import RawResult
from models.cleaned_result import CleanedResult

logger = structlog.get_logger()


class CleaningPipeline:
    """
    Processes raw scraper results through a 7-step cleaning pipeline.
    
    The pipeline ensures data quality through normalization, deduplication,
    validation, and completeness scoring before saving to the database.
    """
    
    # 14 key fields for completeness scoring
    KEY_FIELDS = [
        "name", "address", "city", "phone_primary", "email", "website",
        "rating_overall", "review_count", "thumbnail_url", "description_short",
        "amenities", "price_min", "latitude", "longitude"
    ]

    # Bonus fields from Go scraper — boost completeness score when present
    GO_BONUS_FIELDS = [
        "opening_hours", "source_url",  # mapped to standard columns
    ]
    
    def __init__(self, db: Session):
        """
        Initialize the cleaning pipeline.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def process(self, raw_results: list[dict], job_id: str, source_id: int, category_id: int) -> tuple[list[dict], int]:
        """
        Run all 7 cleaning steps in order.
        
        Args:
            raw_results: List of raw scraper result dictionaries
            job_id: UUID of the scrape job
            source_id: ID of the source that produced these results
            category_id: ID of the category for these results
            
        Returns:
            Tuple of (cleaned result dictionaries, updated record count)
        """
        logger.info(
            "pipeline.started",
            job_id=job_id,
            source_id=source_id,
            result_count=len(raw_results)
        )
        
        # Step 1: Save raw results
        self._save_raw_results(raw_results, job_id, source_id)
        
        # Step 2: Normalize
        normalized = [self._normalize(r) for r in raw_results]
        
        # Step 3: Within-job deduplication
        deduplicated = self._dedup_within_job(normalized, job_id)
        
        # Step 4: Cross-job deduplication (returns non-duplicates and update count)
        flagged, updated_count = self._dedup_cross_job(deduplicated, category_id, job_id)
        
        # Filter out duplicates - they were already updated in _dedup_cross_job
        # Only new records should be saved to cleaned_results table
        non_duplicates = [r for r in flagged if not r.get("is_duplicate", False)]
        
        # Step 5: Validate
        validated = [self._validate(r) for r in non_duplicates]
        
        # Step 6: Compute completeness
        scored = [self._compute_completeness(r) for r in validated]
        
        # Step 7: Save cleaned results (only new records, not duplicates)
        self._save_cleaned_results(scored, job_id, source_id, category_id)
        
        logger.info(
            "pipeline.complete",
            job_id=job_id,
            source_id=source_id,
            total_scraped=len(raw_results),
            new_records_saved=len(scored),
            existing_records_updated=updated_count,
            duplicates_skipped=len(raw_results) - len(scored) - updated_count
        )
        
        return scored, updated_count
    
    def _save_raw_results(self, raw_results: list[dict], job_id: str, source_id: int) -> None:
        """
        Save raw results to raw_results table for audit trail.
        
        Args:
            raw_results: List of raw result dictionaries
            job_id: UUID of the scrape job
            source_id: ID of the source
        """
        for result in raw_results:
            raw_record = RawResult(
                job_id=job_id,
                source_id=source_id,
                raw_data=result
            )
            self.db.add(raw_record)
        
        self.db.commit()
    
    def _normalize(self, result: dict) -> dict:
        """
        Normalize fields: strip whitespace, format phones, ensure https://, convert ratings.
        
        Normalization rules:
        - Strip leading/trailing whitespace from all text fields
        - Format phone numbers: remove non-digits, keep only digits and +
        - Ensure website URLs start with https:// (add if missing)
        - Convert rating strings to float (handle "8.5/10" → 8.5)
        - Store original casing for names and addresses
        
        Args:
            result: Raw result dictionary
            
        Returns:
            Normalized result dictionary
        """
        normalized = result.copy()
        
        # Strip whitespace from all string fields
        for key, value in normalized.items():
            if isinstance(value, str):
                normalized[key] = value.strip()
        
        # Format phone numbers (keep only digits and +)
        for phone_field in ["phone_primary", "phone_secondary", "whatsapp_number"]:
            if phone_field in normalized and normalized[phone_field]:
                phone = normalized[phone_field]
                # Keep only digits and +
                normalized[phone_field] = re.sub(r'[^\d+]', '', phone)
        
        # Ensure website URLs start with https://
        if "website" in normalized and normalized["website"]:
            website = normalized["website"]
            if not website.startswith(("http://", "https://")):
                normalized["website"] = f"https://{website}"
            elif website.startswith("http://"):
                normalized["website"] = website.replace("http://", "https://", 1)
        
        # Convert rating strings to float
        for rating_field in [
            "rating_overall", "rating_cleanliness", "rating_location",
            "rating_facilities", "rating_service", "rating_value"
        ]:
            if rating_field in normalized and normalized[rating_field]:
                rating = normalized[rating_field]
                if isinstance(rating, str):
                    # Handle formats like "8.5/10" or "8.5"
                    match = re.match(r'([\d.]+)(?:/\d+)?', rating)
                    if match:
                        try:
                            normalized[rating_field] = float(match.group(1))
                        except ValueError:
                            pass  # Keep original if conversion fails
        
        return normalized
    
    def _dedup_within_job(self, results: list[dict], job_id: str) -> list[dict]:
        """
        Deduplicate within the same job batch.
        
        Generate dedup_key from SHA-256(lowercase(name) + lowercase(city)).
        Skip if key already seen in this job batch. First occurrence is kept.
        
        Args:
            results: List of normalized result dictionaries
            job_id: UUID of the scrape job
            
        Returns:
            List of deduplicated results
        """
        logger.info(
            "dedup.within_job.started",
            job_id=job_id,
            result_count=len(results)
        )
        
        seen_keys = set()
        deduplicated = []
        duplicate_count = 0
        
        for idx, result in enumerate(results):
            # Generate dedup key
            name = result.get("name", "").lower()
            city = result.get("city", "").lower()
            dedup_key = self._generate_dedup_key(name, city)
            
            # Add dedup_key to result
            result["dedup_key"] = dedup_key
            
            # Mark as duplicate if already seen, but still include so MergingPipeline can access it
            if dedup_key in seen_keys:
                logger.debug(
                    "dedup.duplicate_found",
                    job_id=job_id,
                    idx=idx,
                    name=name,
                    city=city,
                    dedup_key_prefix=dedup_key[:16]
                )
                result["is_duplicate"] = True
                duplicate_count += 1
            else:
                seen_keys.add(dedup_key)
                result["is_duplicate"] = False
            
            deduplicated.append(result)
        
        logger.info(
            "dedup.within_job.complete",
            job_id=job_id,
            duplicates=duplicate_count,
            kept=len(deduplicated),
            unique_keys=len(seen_keys)
        )
        
        return deduplicated
    
    def _dedup_cross_job(self, results: list[dict], category_id: int, job_id: str) -> tuple[list[dict], int]:
        """
        Deduplicate against existing records in cleaned_results with SMART MERGE.
        
        Query cleaned_results for existing rows with same dedup_key and category_id.
        If found, UPDATE changed fields in existing record (don't skip).
        Only update fields that:
        1. New value is not None
        2. New value is different from existing
        3. Field is not manually edited (is_edited=False)
        
        Args:
            results: List of deduplicated result dictionaries
            category_id: ID of the category
            job_id: UUID of the scrape job
            
        Returns:
            Tuple of (non-duplicate results list, updated record count)
        """
        # Fields that can be updated via smart merge
        UPDATABLE_FIELDS = [
            'phone_primary', 'phone_secondary', 'whatsapp_number',
            'email', 'website', 'facebook_url', 'instagram_handle',
            'address', 'street_address', 'latitude', 'longitude',
            'price_min', 'price_max', 'price_range_label',
            'rating_overall', 'review_count', 'rating_cleanliness',
            'rating_location', 'rating_facilities', 'rating_service', 'rating_value',
            'thumbnail_url', 'image_urls', 'image_count',
            'description_short', 'description_full', 'highlights',
            'amenities', 'opening_hours', 'checkin_time', 'checkout_time',
            'star_rating', 'cancellation_policy', 'free_cancellation',
            'pets_allowed', 'breakfast_available', 'includes_breakfast',
            'includes_taxes', 'established_year', 'extra_data'
        ]
        
        duplicate_count = 0
        updated_count = 0
        non_duplicates = []
        
        for result in results:
            dedup_key = result.get("dedup_key")
            
            if dedup_key:
                # Query for existing record with same dedup_key and category_id
                existing = self.db.query(CleanedResult).filter(
                    CleanedResult.dedup_key == dedup_key,
                    CleanedResult.category_id == category_id
                ).first()
                
                if existing:
                    # SMART MERGE: Update existing record with new data
                    updated_fields = []
                    
                    # Never update manually edited records
                    if not existing.is_edited:
                        for field in UPDATABLE_FIELDS:
                            new_val = result.get(field)
                            old_val = getattr(existing, field, None)
                            
                            # Normalize phone numbers before comparison to avoid false positives
                            if field in ['phone_primary', 'phone_secondary', 'whatsapp_number']:
                                new_val_normalized = self._normalize_phone(new_val) if new_val else None
                                old_val_normalized = self._normalize_phone(old_val) if old_val else None
                                
                                # Only update if normalized values are different
                                if new_val_normalized and new_val_normalized != old_val_normalized:
                                    setattr(existing, field, new_val)
                                    updated_fields.append(field)
                                continue
                            
                            # Update if new value is not None and different from existing
                            if new_val is not None and new_val != old_val:
                                # Convert to Decimal for numeric fields
                                if field in ['latitude', 'longitude', 'price_min', 'price_max',
                                           'rating_overall', 'rating_cleanliness', 'rating_location',
                                           'rating_facilities', 'rating_service', 'rating_value']:
                                    new_val = self._to_decimal(new_val)
                                
                                setattr(existing, field, new_val)
                                updated_fields.append(field)
                        
                        if updated_fields:
                            # Update metadata
                            existing.updated_at = datetime.utcnow()
                            existing.scraper_source = result.get('scraper_source', existing.scraper_source)
                            
                            # Track which sources contributed to this merged record
                            source_id = result.get('source_id')
                            if source_id:
                                merged_sources = existing.merged_from_sources or []
                                if source_id not in merged_sources:
                                    existing.merged_from_sources = merged_sources + [source_id]
                            
                            # Recompute completeness score
                            completeness_result = self._compute_completeness(result)
                            existing.data_completeness = self._to_decimal(
                                completeness_result.get('data_completeness')
                            )
                            
                            updated_count += 1
                            
                            logger.info(
                                "dedup.record_updated",
                                job_id=job_id,
                                name=existing.name,
                                dedup_key_prefix=dedup_key[:16],
                                fields_updated=updated_fields,
                                field_count=len(updated_fields)
                            )
                    else:
                        logger.debug(
                            "dedup.skip_edited_record",
                            job_id=job_id,
                            name=existing.name,
                            dedup_key_prefix=dedup_key[:16],
                            reason="manually_edited"
                        )
                    
                    # Mark as duplicate (don't add to non_duplicates list)
                    result["is_duplicate"] = True
                    duplicate_count += 1
                else:
                    # New record - not a duplicate
                    if not result.get("is_duplicate", False):
                        result["is_duplicate"] = False
                    non_duplicates.append(result)
            else:
                # No dedup key - keep as non-duplicate
                if not result.get("is_duplicate", False):
                    result["is_duplicate"] = False
                non_duplicates.append(result)
        
        # Commit updates to existing records
        if updated_count > 0:
            self.db.commit()
        
        logger.info(
            "dedup.cross_job.complete",
            job_id=job_id,
            total_input=len(results),
            duplicates_found=duplicate_count,
            records_updated=updated_count,
            new_records=len(non_duplicates)
        )
        
        # Return non-duplicate results and update count
        return non_duplicates, updated_count
    
    def _validate(self, result: dict) -> dict:
        """
        Validate fields and set invalid fields to NULL.
        
        Validation rules:
        - Phone must contain digits
        - Email must contain @
        - Rating must be 0-10
        - Latitude must be -90 to 90
        - Longitude must be -180 to 180
        
        If validation fails, set that field to NULL. Do not reject the whole record.
        
        Args:
            result: Result dictionary
            
        Returns:
            Validated result dictionary
        """
        validated = result.copy()
        
        # Validate phone fields (must contain digits)
        for phone_field in ["phone_primary", "phone_secondary", "whatsapp_number"]:
            if phone_field in validated and validated[phone_field]:
                phone = validated[phone_field]
                if not re.search(r'\d', phone):
                    validated[phone_field] = None
        
        # Validate email (must contain @)
        if "email" in validated and validated["email"]:
            email = validated["email"]
            if "@" not in email:
                validated["email"] = None
        
        # Validate rating fields (must be 0-10)
        for rating_field in [
            "rating_overall", "rating_cleanliness", "rating_location",
            "rating_facilities", "rating_service", "rating_value"
        ]:
            if rating_field in validated and validated[rating_field] is not None:
                try:
                    rating = float(validated[rating_field])
                    if rating < 0 or rating > 10:
                        validated[rating_field] = None
                except (ValueError, TypeError):
                    validated[rating_field] = None
        
        # Validate latitude (-90 to 90)
        if "latitude" in validated and validated["latitude"] is not None:
            try:
                lat = float(validated["latitude"])
                if lat < -90 or lat > 90:
                    validated["latitude"] = None
            except (ValueError, TypeError):
                validated["latitude"] = None
        
        # Validate longitude (-180 to 180)
        if "longitude" in validated and validated["longitude"] is not None:
            try:
                lon = float(validated["longitude"])
                if lon < -180 or lon > 180:
                    validated["longitude"] = None
            except (ValueError, TypeError):
                validated["longitude"] = None
        
        return validated
    
    def _compute_completeness(self, result: dict) -> dict:
        """
        Compute data completeness percentage.
        
        Count non-NULL fields from 14 key fields and compute percentage.
        Formula: (count of non-NULL fields / 14) * 100
        
        Go scraper results get a bonus for extra_data richness.
        """
        non_null_count = 0
        
        for field in self.KEY_FIELDS:
            if field in result and result[field] is not None:
                if isinstance(result[field], str):
                    if result[field].strip():
                        non_null_count += 1
                else:
                    non_null_count += 1
        
        completeness = (non_null_count / len(self.KEY_FIELDS)) * 100

        # Bonus for Go scraper extra_data richness (up to +10%)
        extra_data = result.get("extra_data")
        if extra_data and isinstance(extra_data, dict):
            bonus_fields = ["place_id", "open_hours", "user_reviews", "images",
                            "complete_address", "popular_times"]
            bonus_count = sum(1 for f in bonus_fields if extra_data.get(f))
            completeness = min(100.0, completeness + (bonus_count * 1.5))

        result["data_completeness"] = round(completeness, 2)
        
        return result
    
    def _save_cleaned_results(
        self,
        results: list[dict],
        job_id: str,
        source_id: int,
        category_id: int
    ) -> None:
        """
        Save cleaned results to cleaned_results table.
        
        Args:
            results: List of cleaned result dictionaries
            job_id: UUID of the scrape job
            source_id: ID of the source
            category_id: ID of the category
        """
        for result in results:
            # Prepare cleaned record
            cleaned_record = CleanedResult(
                job_id=job_id,
                source_id=source_id,
                category_id=category_id,
                dedup_key=result.get("dedup_key"),
                
                # Identity
                name=result.get("name"),
                brand=result.get("brand"),
                property_type=result.get("property_type"),
                star_rating=result.get("star_rating"),
                
                # Location
                address=result.get("address"),
                street_address=result.get("street_address"),
                city=result.get("city"),
                district=result.get("district"),
                province=result.get("province"),
                country=result.get("country", "Nepal"),
                latitude=self._to_decimal(result.get("latitude")),
                longitude=self._to_decimal(result.get("longitude")),
                neighbourhood=result.get("neighbourhood"),
                nearby_landmark=result.get("nearby_landmark"),
                
                # Contact
                phone_primary=result.get("phone_primary"),
                phone_secondary=result.get("phone_secondary"),
                email=result.get("email"),
                website=result.get("website"),
                facebook_url=result.get("facebook_url"),
                instagram_handle=result.get("instagram_handle"),
                whatsapp_number=result.get("whatsapp_number"),
                
                # Pricing
                price_min=self._to_decimal(result.get("price_min")),
                price_max=self._to_decimal(result.get("price_max")),
                currency=result.get("currency", "NPR"),
                price_range_label=result.get("price_range_label"),
                includes_breakfast=result.get("includes_breakfast"),
                includes_taxes=result.get("includes_taxes"),
                
                # Reviews
                rating_overall=self._to_decimal(result.get("rating_overall")),
                rating_label=result.get("rating_label"),
                review_count=result.get("review_count"),
                rating_cleanliness=self._to_decimal(result.get("rating_cleanliness")),
                rating_location=self._to_decimal(result.get("rating_location")),
                rating_facilities=self._to_decimal(result.get("rating_facilities")),
                rating_service=self._to_decimal(result.get("rating_service")),
                rating_value=self._to_decimal(result.get("rating_value")),
                
                # Facilities
                amenities=result.get("amenities"),
                pets_allowed=result.get("pets_allowed"),
                breakfast_available=result.get("breakfast_available"),
                checkin_time=result.get("checkin_time"),
                checkout_time=result.get("checkout_time"),
                cancellation_policy=result.get("cancellation_policy"),
                free_cancellation=result.get("free_cancellation"),
                
                # Media
                thumbnail_url=result.get("thumbnail_url"),
                image_urls=result.get("image_urls"),
                image_count=result.get("image_count"),
                
                # Content
                description_short=result.get("description_short"),
                description_full=result.get("description_full"),
                highlights=result.get("highlights"),
                popular_with=result.get("popular_with"),
                staff_languages=result.get("staff_languages"),
                
                # Business Info
                opening_hours=result.get("opening_hours"),
                established_year=result.get("established_year"),
                
                # Metadata
                source_url=result.get("source_url"),
                source_listing_id=result.get("source_listing_id"),
                data_completeness=self._to_decimal(result.get("data_completeness")),
                is_edited=False,
                is_duplicate=result.get("is_duplicate", False),
                status="PENDING",

                # Go scraper integration
                scraper_source=result.get("scraper_source"),
                extra_data=result.get("extra_data") or None,
            )
            
            self.db.add(cleaned_record)
        
        self.db.commit()
    
    @staticmethod
    def _generate_dedup_key(name: str, city: str) -> str:
        """
        Generate SHA-256 dedup key from lowercase name and city.
        
        Args:
            name: Business name
            city: City name
            
        Returns:
            SHA-256 hash as hex string
        """
        normalized = f"{name.lower()}{city.lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """
        Convert value to Decimal for database storage.
        
        Args:
            value: Value to convert
            
        Returns:
            Decimal value or None
        """
        if value is None:
            return None
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _normalize_phone(phone: Any) -> str | None:
        """
        Normalize phone number by removing all formatting characters.
        
        This prevents false positives when comparing phone numbers:
        - "061450617" and "061-450617" are the same
        - "9806639804" and "980-6639804" are the same
        
        Args:
            phone: Phone number string (may include dashes, spaces, parentheses)
            
        Returns:
            Normalized phone string (digits and + only) or None
        """
        if not phone:
            return None
        
        phone_str = str(phone).strip()
        if not phone_str:
            return None
        
        # Remove all formatting: dashes, spaces, parentheses, dots
        # Keep only digits and + (for international prefix)
        normalized = re.sub(r'[^\d+]', '', phone_str)
        
        return normalized if normalized else None
