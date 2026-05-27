"""
Merging Pipeline for Web Scraping Portal

This module merges results from multiple sources to create enriched records.
When the same business appears in multiple sources (e.g., Booking.com + Google Maps),
it combines the data to create a single record with the best information from all sources.

Strategy:
1. Group results by dedup_key (same business from different sources)
2. For each group, merge fields using priority rules
3. Update one result as "master" with merged data
4. Mark others as duplicates (is_duplicate=TRUE)
5. Track source_ids in merged_from_sources array
6. Calculate confidence_score based on number of sources
"""

import structlog
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.cleaned_result import CleanedResult

logger = structlog.get_logger()


class MergingPipeline:
    """
    Merges results from multiple sources to create enriched records.
    
    Merging Rules:
    - Prefer non-null values over null
    - Prefer higher data_completeness scores
    - Prefer Go scraper for rich fields (opening_hours, extra_data)
    - Prefer Booking.com/Agoda for pricing and amenities
    - Combine arrays (amenities, image_urls)
    - Average numeric values (ratings) if different
    """
    
    # Source priority for different field types
    PRICE_SOURCES = ["booking_com", "agoda", "tripadvisor"]  # Best for pricing
    RICH_DATA_SOURCES = ["google_maps"]  # Best for opening hours, reviews, images
    CONTACT_SOURCES = ["nepalyp", "directoryofnepal"]  # Best for phone, email
    
    def __init__(self, db: Session):
        """
        Initialize the merging pipeline.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def run(self, job_id: str) -> Dict[str, int]:
        """
        Run merging pipeline for all results in a job.
        
        Args:
            job_id: UUID of the scrape job
            
        Returns:
            Dictionary with merge statistics:
            - merged_groups: Number of groups that were merged
            - total_records_processed: Total number of records processed
            - master_records: Number of master records created
            - duplicate_records: Number of records marked as duplicates
        """
        logger.info("merger.started", job_id=job_id)
        
        # Load all cleaned results for this job
        results = self.db.query(CleanedResult).filter(
            CleanedResult.job_id == job_id
        ).all()
        
        if not results:
            logger.info("merger.no_results", job_id=job_id)
            return {
                "merged_groups": 0,
                "total_records_processed": 0,
                "master_records": 0,
                "duplicate_records": 0
            }
        
        logger.info(
            "merger.results_loaded",
            job_id=job_id,
            result_count=len(results)
        )
        
        # Group results by dedup_key
        groups = self._group_by_dedup_key(results)
        
        logger.info(
            "merger.groups_created",
            job_id=job_id,
            total_results=len(results),
            unique_groups=len(groups),
            multi_source_groups=sum(1 for g in groups.values() if len(g) > 1)
        )
        
        # Merge each group
        merged_groups = 0
        master_records = 0
        duplicate_records = 0
        
        for dedup_key, group_results in groups.items():
            if len(group_results) > 1:
                # Multiple sources for same business — merge them
                master, duplicates = self._merge_group(group_results)
                merged_groups += 1
                master_records += 1
                duplicate_records += len(duplicates)
                
                logger.debug(
                    "merger.group_merged",
                    job_id=job_id,
                    dedup_key=dedup_key[:16],
                    source_count=len(group_results),
                    master_id=str(master.id),
                    master_sources=master.merged_from_sources,
                    confidence=float(master.confidence_score) if master.confidence_score else None
                )
        
        # Commit all changes
        self.db.commit()
        
        stats = {
            "merged_groups": merged_groups,
            "total_records_processed": len(results),
            "master_records": master_records,
            "duplicate_records": duplicate_records
        }
        
        logger.info(
            "merger.completed",
            job_id=job_id,
            **stats
        )
        
        return stats
    
    def _group_by_dedup_key(self, results: List[CleanedResult]) -> Dict[str, List[CleanedResult]]:
        """
        Group results by dedup_key.
        
        Args:
            results: List of CleanedResult objects
            
        Returns:
            Dictionary mapping dedup_key to list of results
        """
        groups = {}
        
        for result in results:
            if result.dedup_key:
                if result.dedup_key not in groups:
                    groups[result.dedup_key] = []
                groups[result.dedup_key].append(result)
        
        return groups
    
    def _merge_group(self, group: List[CleanedResult]) -> tuple[CleanedResult, List[CleanedResult]]:
        """
        Merge a group of results from different sources.
        
        Strategy:
        1. Choose master record (highest completeness)
        2. Merge fields from all sources into master
        3. Mark others as duplicates
        4. Set merged_from_sources and confidence_score
        
        Args:
            group: List of CleanedResult objects with same dedup_key
            
        Returns:
            Tuple of (master_record, duplicate_records)
        """
        # Sort by data_completeness (highest first)
        sorted_group = sorted(
            group,
            key=lambda r: r.data_completeness or 0,
            reverse=True
        )
        
        # Choose master (highest completeness)
        master = sorted_group[0]
        duplicates = sorted_group[1:]
        
        # Collect source IDs
        source_ids = [r.source_id for r in group]
        
        # Merge fields from all sources
        for result in group:
            if result.id == master.id:
                continue  # Skip master itself
            
            # Merge each field using priority rules
            master = self._merge_fields(master, result)
        
        # Set merge metadata
        master.merged_from_sources = source_ids
        master.confidence_score = self._calculate_confidence(len(source_ids))
        master.merged_at = datetime.utcnow()
        
        # Mark duplicates
        for dup in duplicates:
            dup.is_duplicate = True
        
        return master, duplicates
    
    def _merge_fields(self, master: CleanedResult, source: CleanedResult) -> CleanedResult:
        """
        Merge fields from source into master using priority rules.
        
        Rules:
        - Prefer non-null over null
        - Prefer higher completeness for text fields
        - Combine arrays (amenities, image_urls)
        - Average numeric values if both present
        - Prefer specific sources for specific fields
        
        Args:
            master: Master record to merge into
            source: Source record to merge from
            
        Returns:
            Updated master record
        """
        # Get source names for priority decisions
        master_source = self._get_source_name(master.source_id)
        source_source = self._get_source_name(source.source_id)
        
        # Identity fields (prefer non-null)
        master.brand = master.brand or source.brand
        master.property_type = master.property_type or source.property_type
        master.star_rating = master.star_rating or source.star_rating
        
        # Location fields (prefer non-null, prefer longer addresses)
        if not master.address or (source.address and len(source.address) > len(master.address)):
            master.address = source.address
        master.street_address = master.street_address or source.street_address
        master.district = master.district or source.district
        master.province = master.province or source.province
        master.neighbourhood = master.neighbourhood or source.neighbourhood
        master.nearby_landmark = master.nearby_landmark or source.nearby_landmark
        
        # Coordinates (prefer non-null, prefer Go scraper)
        if not master.latitude and source.latitude:
            master.latitude = source.latitude
            master.longitude = source.longitude
        elif source_source == "google_maps" and source.latitude:
            # Override with Google Maps coordinates (more accurate)
            master.latitude = source.latitude
            master.longitude = source.longitude
        
        # Contact fields (prefer non-null, prefer contact-focused sources)
        if not master.phone_primary or source_source in self.CONTACT_SOURCES:
            master.phone_primary = master.phone_primary or source.phone_primary
        master.phone_secondary = master.phone_secondary or source.phone_secondary
        master.email = master.email or source.email
        
        # Website (prefer non-null)
        master.website = master.website or source.website
        master.facebook_url = master.facebook_url or source.facebook_url
        master.instagram_handle = master.instagram_handle or source.instagram_handle
        master.whatsapp_number = master.whatsapp_number or source.whatsapp_number
        
        # Pricing (prefer price-focused sources like Booking.com)
        if not master.price_min or source_source in self.PRICE_SOURCES:
            master.price_min = master.price_min or source.price_min
            master.price_max = master.price_max or source.price_max
            master.price_range_label = master.price_range_label or source.price_range_label
        master.includes_breakfast = master.includes_breakfast or source.includes_breakfast
        master.includes_taxes = master.includes_taxes or source.includes_taxes
        
        # Reviews (average if both present, otherwise prefer non-null)
        if master.rating_overall and source.rating_overall:
            # Average ratings
            master.rating_overall = (master.rating_overall + source.rating_overall) / 2
        else:
            master.rating_overall = master.rating_overall or source.rating_overall
        
        master.rating_label = master.rating_label or source.rating_label
        
        # Review count (sum if both present)
        if master.review_count and source.review_count:
            master.review_count = master.review_count + source.review_count
        else:
            master.review_count = master.review_count or source.review_count
        
        # Detailed ratings (average if both present)
        for rating_field in ['rating_cleanliness', 'rating_location', 'rating_facilities', 
                             'rating_service', 'rating_value']:
            master_val = getattr(master, rating_field)
            source_val = getattr(source, rating_field)
            if master_val and source_val:
                setattr(master, rating_field, (master_val + source_val) / 2)
            else:
                setattr(master, rating_field, master_val or source_val)
        
        # Facilities (combine arrays)
        master.amenities = self._merge_json_arrays(master.amenities, source.amenities)
        master.pets_allowed = master.pets_allowed or source.pets_allowed
        master.breakfast_available = master.breakfast_available or source.breakfast_available
        master.checkin_time = master.checkin_time or source.checkin_time
        master.checkout_time = master.checkout_time or source.checkout_time
        master.cancellation_policy = master.cancellation_policy or source.cancellation_policy
        master.free_cancellation = master.free_cancellation or source.free_cancellation
        
        # Media (combine arrays, prefer higher count)
        master.thumbnail_url = master.thumbnail_url or source.thumbnail_url
        master.image_urls = self._merge_json_arrays(master.image_urls, source.image_urls)
        if master.image_count and source.image_count:
            master.image_count = max(master.image_count, source.image_count)
        else:
            master.image_count = master.image_count or source.image_count
        
        # Content (prefer longer descriptions)
        if not master.description_short or (source.description_short and 
                                            len(source.description_short) > len(master.description_short or "")):
            master.description_short = source.description_short
        if not master.description_full or (source.description_full and 
                                           len(source.description_full) > len(master.description_full or "")):
            master.description_full = source.description_full
        
        master.highlights = self._merge_json_arrays(master.highlights, source.highlights)
        master.popular_with = self._merge_json_arrays(master.popular_with, source.popular_with)
        master.staff_languages = self._merge_json_arrays(master.staff_languages, source.staff_languages)
        
        # Business info (prefer Go scraper for opening hours)
        if not master.opening_hours or source_source in self.RICH_DATA_SOURCES:
            master.opening_hours = master.opening_hours or source.opening_hours
        master.established_year = master.established_year or source.established_year
        
        # Metadata
        master.source_url = master.source_url or source.source_url
        master.source_listing_id = master.source_listing_id or source.source_listing_id
        
        # Go scraper fields (prefer Go scraper)
        if source_source == "google_maps" or not master.scraper_source:
            master.scraper_source = source.scraper_source or master.scraper_source
        
        # Merge extra_data (combine dictionaries)
        if source.extra_data:
            if not master.extra_data:
                master.extra_data = source.extra_data
            else:
                # Merge dictionaries (source values override master if present)
                master.extra_data = {**master.extra_data, **source.extra_data}
        
        # Recalculate completeness after merge
        master.data_completeness = self._recalculate_completeness(master)
        
        return master
    
    def _merge_json_arrays(self, master_array: Any, source_array: Any) -> Any:
        """
        Merge two JSON arrays, removing duplicates.
        
        Args:
            master_array: Master array (list or None)
            source_array: Source array (list or None)
            
        Returns:
            Merged array with unique values
        """
        if not master_array and not source_array:
            return None
        
        if not master_array:
            return source_array
        
        if not source_array:
            return master_array
        
        # Ensure both are lists
        if not isinstance(master_array, list):
            master_array = [master_array]
        if not isinstance(source_array, list):
            source_array = [source_array]
        
        # Combine and remove duplicates (preserve order)
        seen = set()
        merged = []
        for item in master_array + source_array:
            # Convert to string for comparison (handles dicts, strings, etc.)
            item_str = str(item)
            if item_str not in seen:
                seen.add(item_str)
                merged.append(item)
        
        return merged if merged else None
    
    def _calculate_confidence(self, source_count: int) -> Decimal:
        """
        Calculate confidence score based on number of sources.
        
        Formula:
        - 1 source: 0.50 (low confidence)
        - 2 sources: 0.75 (medium confidence)
        - 3+ sources: 0.90 (high confidence)
        
        Args:
            source_count: Number of sources that provided this business
            
        Returns:
            Confidence score (0.00-1.00)
        """
        if source_count >= 3:
            return Decimal("0.90")
        elif source_count == 2:
            return Decimal("0.75")
        else:
            return Decimal("0.50")
    
    def _recalculate_completeness(self, result: CleanedResult) -> Decimal:
        """
        Recalculate data completeness after merging.
        
        Uses same 14 key fields as CleaningPipeline.
        
        Args:
            result: CleanedResult object
            
        Returns:
            Completeness percentage (0.00-100.00)
        """
        key_fields = [
            "name", "address", "city", "phone_primary", "email", "website",
            "rating_overall", "review_count", "thumbnail_url", "description_short",
            "amenities", "price_min", "latitude", "longitude"
        ]
        
        non_null_count = 0
        for field in key_fields:
            value = getattr(result, field, None)
            if value is not None:
                if isinstance(value, str) and value.strip():
                    non_null_count += 1
                elif not isinstance(value, str):
                    non_null_count += 1
        
        completeness = (non_null_count / len(key_fields)) * 100
        
        # Bonus for Go scraper extra_data
        if result.extra_data and isinstance(result.extra_data, dict):
            bonus_fields = ["place_id", "open_hours", "user_reviews", "images",
                            "complete_address", "popular_times"]
            bonus_count = sum(1 for f in bonus_fields if result.extra_data.get(f))
            completeness = min(100.0, completeness + (bonus_count * 1.5))
        
        return Decimal(str(round(completeness, 2)))
    
    def _get_source_name(self, source_id: int) -> str:
        """
        Get source name from source_id.
        
        Args:
            source_id: ID of the source
            
        Returns:
            Source name (e.g., "booking_com", "google_maps")
        """
        # Cache source names to avoid repeated queries
        if not hasattr(self, '_source_cache'):
            self._source_cache = {}
        
        if source_id not in self._source_cache:
            from models.source import Source
            source = self.db.query(Source).filter(Source.id == source_id).first()
            self._source_cache[source_id] = source.name if source else "unknown"
        
        return self._source_cache[source_id]
