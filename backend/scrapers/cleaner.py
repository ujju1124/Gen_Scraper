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
    
    def __init__(self, db: Session):
        """
        Initialize the cleaning pipeline.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def process(self, raw_results: list[dict], job_id: str, source_id: int, category_id: int) -> list[dict]:
        """
        Run all 7 cleaning steps in order.
        
        Args:
            raw_results: List of raw scraper result dictionaries
            job_id: UUID of the scrape job
            source_id: ID of the source that produced these results
            category_id: ID of the category for these results
            
        Returns:
            List of cleaned result dictionaries
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
        
        # Step 4: Cross-job deduplication
        flagged = self._dedup_cross_job(deduplicated, category_id, job_id)
        
        # Step 5: Validate
        validated = [self._validate(r) for r in flagged]
        
        # Step 6: Compute completeness
        scored = [self._compute_completeness(r) for r in validated]
        
        # Step 7: Save cleaned results
        self._save_cleaned_results(scored, job_id, source_id, category_id)
        
        logger.info(
            "pipeline.complete",
            job_id=job_id,
            source_id=source_id,
            total_results=len(raw_results),
            saved_results=len(scored)
        )
        
        return scored
    
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
        seen_keys = set()
        deduplicated = []
        duplicate_count = 0
        
        for result in results:
            # Generate dedup key
            name = result.get("name", "").lower()
            city = result.get("city", "").lower()
            dedup_key = self._generate_dedup_key(name, city)
            
            # Add dedup_key to result
            result["dedup_key"] = dedup_key
            
            # Mark as duplicate if already seen, but still include so MergingPipeline can access it
            if dedup_key in seen_keys:
                result["is_duplicate"] = True
                duplicate_count += 1
            else:
                seen_keys.add(dedup_key)
                result["is_duplicate"] = False
            
            deduplicated.append(result)
        
        if duplicate_count > 0:
            logger.info(
                "dedup.within_job",
                job_id=job_id,
                duplicates=duplicate_count,
                kept=len(deduplicated)
            )
        
        return deduplicated
    
    def _dedup_cross_job(self, results: list[dict], category_id: int, job_id: str) -> list[dict]:
        """
        Deduplicate against existing records in cleaned_results.
        
        Query cleaned_results for existing rows with same dedup_key and category_id.
        If found, set is_duplicate=TRUE and still insert (for audit).
        
        Args:
            results: List of deduplicated result dictionaries
            category_id: ID of the category
            job_id: UUID of the scrape job
            
        Returns:
            List of results with is_duplicate flag set
        """
        duplicate_count = 0
        
        for result in results:
            dedup_key = result.get("dedup_key")
            
            if dedup_key:
                # Query for existing record with same dedup_key and category_id
                existing = self.db.query(CleanedResult).filter(
                    CleanedResult.dedup_key == dedup_key,
                    CleanedResult.category_id == category_id
                ).first()
                
                if existing:
                    result["is_duplicate"] = True
                    duplicate_count += 1
                else:
                    # Only set False if within-job dedup didn't already mark it as duplicate
                    if not result.get("is_duplicate", False):
                        result["is_duplicate"] = False
            else:
                if not result.get("is_duplicate", False):
                    result["is_duplicate"] = False
        
        if duplicate_count > 0:
            logger.info(
                "dedup.cross_job",
                job_id=job_id,
                duplicates=duplicate_count,
                total=len(results)
            )
        
        return results
    
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
        
        14 key fields: name, address, city, phone_primary, email, website,
        rating_overall, review_count, thumbnail_url, description_short,
        amenities, price_min, latitude, longitude
        
        Args:
            result: Result dictionary
            
        Returns:
            Result dictionary with data_completeness field
        """
        non_null_count = 0
        
        for field in self.KEY_FIELDS:
            if field in result and result[field] is not None:
                # Check for non-empty strings
                if isinstance(result[field], str):
                    if result[field].strip():
                        non_null_count += 1
                else:
                    non_null_count += 1
        
        completeness = (non_null_count / len(self.KEY_FIELDS)) * 100
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
                
                # Metadata
                source_url=result.get("source_url"),
                source_listing_id=result.get("source_listing_id"),
                data_completeness=self._to_decimal(result.get("data_completeness")),
                is_edited=False,
                is_duplicate=result.get("is_duplicate", False),
                status="PENDING"
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
