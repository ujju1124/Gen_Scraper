"""
Tests for monitoring dashboard endpoint.
"""
import pytest
import uuid
from sqlalchemy import text
from models import ScrapeJob, CleanedResult, RawResult, ValidatedResult, Source
from datetime import datetime, timedelta


class TestMonitoringEndpoint:
    """Test suite for GET /api/v1/admin/monitoring endpoint."""
    
    def test_monitoring_returns_200_for_admin(self, admin_client):
        """Test that monitoring endpoint returns 200 for admin users."""
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields present
        assert "job_success_rate" in data
        assert "scraper_health" in data
        assert "results_per_source" in data
        assert "avg_job_duration_seconds" in data
        assert "total_results" in data
        assert "recent_failures" in data
    
    def test_monitoring_returns_403_for_non_admin(self, auth_client):
        """Test that monitoring endpoint returns 403 for non-admin users."""
        response = auth_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 403
    
    def test_monitoring_returns_correct_job_success_rate(self, admin_client, db_session, test_user):
        """Test that job success rate is calculated correctly."""
        # Create 3 DONE jobs and 1 FAILED job
        for i in range(3):
            job_id = uuid.uuid4()
            db_session.execute(
                text("""
                    INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                    VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
                """),
                {"job_id": job_id, "user_id": test_user.id}
            )
        
        failed_job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Pokhara', 'FAILED', NOW())
            """),
            {"job_id": failed_job_id, "user_id": test_user.id}
        )
        db_session.commit()
        
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Success rate should be 75% (3 DONE out of 4 total)
        assert data["job_success_rate"] == 75.0
    
    def test_monitoring_returns_results_per_source_counts(self, admin_client, db_session, test_user):
        """Test that results per source counts are correct."""
        # Create a job
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create 5 cleaned results for source_id=1
        for i in range(5):
            db_session.execute(
                text("""
                    INSERT INTO cleaned_results (
                        job_id, source_id, category_id, name, data_completeness, dedup_key
                    )
                    VALUES (:job_id, 1, 1, :name, 0.5, :dedup_key)
                """),
                {"job_id": job_id, "name": f"Business {i}", "dedup_key": f"key-{i}"}
            )
        db_session.commit()
        
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have results_per_source with at least one source
        assert "results_per_source" in data
        assert isinstance(data["results_per_source"], dict)
        
        # Fake Source should have 5 results
        assert "fake_source" in data["results_per_source"]
        assert data["results_per_source"]["fake_source"] >= 5
    
    def test_monitoring_returns_total_results(self, admin_client, db_session, test_user):
        """Test that total results counts are correct."""
        # Create a job
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create 2 raw results
        for i in range(2):
            db_session.execute(
                text("""
                    INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                    VALUES (:job_id, 1, :raw_data, NOW())
                """),
                {"job_id": job_id, "raw_data": f'{{"test": "data{i}"}}'}
            )
        
        # Create 1 cleaned result
        db_session.execute(
            text("""
                INSERT INTO cleaned_results (
                    job_id, source_id, category_id, name, data_completeness, dedup_key
                )
                VALUES (:job_id, 1, 1, 'Business', 0.5, 'key-1')
            """),
            {"job_id": job_id}
        )
        db_session.commit()
        
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify total_results structure
        assert "total_results" in data
        assert "raw" in data["total_results"]
        assert "cleaned" in data["total_results"]
        assert "validated" in data["total_results"]
        
        # Should have at least the records we created
        assert data["total_results"]["raw"] >= 2
        assert data["total_results"]["cleaned"] >= 1
    
    def test_monitoring_returns_scraper_health(self, admin_client):
        """Test that scraper health list is returned."""
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify scraper_health structure
        assert "scraper_health" in data
        assert isinstance(data["scraper_health"], list)
        
        # Should have at least the fake_source from test setup
        assert len(data["scraper_health"]) >= 1
        
        # Verify structure of first item
        if data["scraper_health"]:
            health_item = data["scraper_health"][0]
            assert "source_id" in health_item
            assert "source_name" in health_item
            assert "is_active" in health_item
            assert "result_count" in health_item
    
    def test_monitoring_returns_recent_failures(self, admin_client, db_session, test_user):
        """Test that recent failures list is returned."""
        # Create a failed job
        failed_job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (
                    id, user_id, category_id, location, status, error_message, created_at
                )
                VALUES (
                    :job_id, :user_id, 1, 'Pokhara', 'FAILED', 
                    'Connection timeout', NOW()
                )
            """),
            {"job_id": failed_job_id, "user_id": test_user.id}
        )
        db_session.commit()
        
        response = admin_client.get("/api/v1/admin/monitoring")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recent_failures structure
        assert "recent_failures" in data
        assert isinstance(data["recent_failures"], list)
        
        # Should have at least the failed job we created
        assert len(data["recent_failures"]) >= 1
        
        # Verify structure of failure item
        if data["recent_failures"]:
            failure = data["recent_failures"][0]
            assert "job_id" in failure
            assert "location" in failure
            assert "sources" in failure
            assert "error_message" in failure
            assert "created_at" in failure
