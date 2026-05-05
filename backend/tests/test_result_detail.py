"""
Tests for result detail endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from main import app
from models import User, CleanedResult, ScrapeJob


def test_get_result_detail_success(client: TestClient, db_session: Session, test_user: User):
    """Test authenticated user can fetch result by ID."""
    # Create a test job
    job = ScrapeJob(
        user_id=test_user.id,
        category_id=1,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create a test cleaned result with comprehensive data
    result = CleanedResult(
        job_id=job.id,
        source_id=1,
        category_id=1,
        name="Test Hotel",
        brand="Test Brand",
        property_type="Hotel",
        star_rating=4,
        address="123 Test Street, Thamel",
        street_address="123 Test Street",
        city="Kathmandu",
        district="Kathmandu",
        province="Bagmati",
        country="Nepal",
        latitude=27.7172,
        longitude=85.324,
        neighbourhood="Thamel",
        nearby_landmark="Near Durbar Square",
        phone_primary="+977-1-4123456",
        phone_secondary="+977-9841234567",
        email="info@testhotel.com",
        website="https://testhotel.com",
        facebook_url="https://facebook.com/testhotel",
        instagram_handle="@testhotel",
        whatsapp_number="+977-9841234567",
        price_min=5000.00,
        price_max=10000.00,
        currency="NPR",
        price_range_label="$$",
        includes_breakfast=True,
        includes_taxes=False,
        rating_overall=8.5,
        rating_label="Excellent",
        review_count=250,
        rating_cleanliness=8.7,
        rating_location=9.0,
        rating_facilities=8.3,
        rating_service=8.6,
        rating_value=8.4,
        amenities=["WiFi", "Parking", "Restaurant", "Pool"],
        pets_allowed=False,
        breakfast_available=True,
        checkin_time="14:00",
        checkout_time="12:00",
        cancellation_policy="Free cancellation up to 24 hours before check-in",
        free_cancellation=True,
        thumbnail_url="https://example.com/thumb.jpg",
        image_urls=["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
        image_count=15,
        description_short="A comfortable hotel in the heart of Thamel",
        description_full="Experience luxury and comfort at Test Hotel, located in the vibrant Thamel district.",
        highlights=["Central location", "Rooftop restaurant", "24/7 service"],
        popular_with=["Couples", "Business travelers"],
        staff_languages=["English", "Nepali", "Hindi"],
        source_url="https://example.com/listing/123",
        source_listing_id="test-123",
        data_completeness=85.5,
        is_edited=False,
        is_duplicate=False,
        status="PENDING"
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    
    # Override get_current_user dependency to return test_user
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        response = client.get(f"/api/v1/jobs/results/{result.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify key fields are present
        assert data["name"] == "Test Hotel"
        assert data["city"] == "Kathmandu"
        assert data["address"] == "123 Test Street, Thamel"
        assert data["phone_primary"] == "+977-1-4123456"
        assert data["email"] == "info@testhotel.com"
        assert data["website"] == "https://testhotel.com"
        assert float(data["price_min"]) == 5000.00
        assert float(data["price_max"]) == 10000.00
        assert data["currency"] == "NPR"
        assert float(data["rating_overall"]) == 8.5
        assert data["review_count"] == 250
        assert float(data["latitude"]) == 27.7172
        assert float(data["longitude"]) == 85.324
        assert data["amenities"] == ["WiFi", "Parking", "Restaurant", "Pool"]
        assert data["checkin_time"] == "14:00"
        assert data["checkout_time"] == "12:00"
        assert float(data["data_completeness"]) == 85.5
        assert data["status"] == "PENDING"
        assert data["is_edited"] is False
        assert data["is_duplicate"] is False
        
    finally:
        app.dependency_overrides.clear()


def test_get_result_detail_unauthenticated(client: TestClient, db_session: Session):
    """Test unauthenticated request returns 401."""
    # Create a dummy result
    job = ScrapeJob(
        user_id=1,
        category_id=1,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    result = CleanedResult(
        job_id=job.id,
        source_id=1,
        category_id=1,
        name="Test",
        status="PENDING"
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    
    # Don't override get_current_user, so it will fail auth
    response = client.get(f"/api/v1/jobs/results/{result.id}")
    
    assert response.status_code == 401


def test_get_result_detail_not_found(client: TestClient, test_user: User):
    """Test non-existent ID returns 404."""
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Use a random UUID that doesn't exist
        non_existent_id = uuid4()
        response = client.get(f"/api/v1/jobs/results/{non_existent_id}")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Result not found"
        
    finally:
        app.dependency_overrides.clear()
