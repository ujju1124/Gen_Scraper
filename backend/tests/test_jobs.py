"""
Integration tests for job endpoints.
"""
import time
import pytest
from models import ScrapeJob, RawResult, CleanedResult


def test_create_job_returns_queued(auth_client, mock_sleep):
    """POST /jobs creates a job with status QUEUED and dispatches Celery task."""
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Kathmandu",
        "source_ids": [1]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "QUEUED"
    assert "id" in data
    assert "celery_task_id" in data


def test_create_job_requires_auth(client):
    """POST /jobs returns 401 if not authenticated."""
    response = client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Kathmandu"
    })
    
    assert response.status_code == 401


def test_fake_task_sets_done(auth_client, db_session, mock_sleep):
    """Fake scraper task completes and sets job status to DONE."""
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Pokhara",
        "source_ids": [1]
    })
    
    assert response.status_code == 201
    job_id = response.json()["id"]
    
    # Celery runs synchronously in tests (task_always_eager=True)
    # Expire session to see changes from Celery task's separate session
    db_session.expire_all()
    
    # Check job status
    job = db_session.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    assert job is not None
    assert job.status == "DONE"
    assert job.started_at is not None
    assert job.completed_at is not None


def test_raw_results_inserted(auth_client, db_session, mock_sleep):
    """Fake scraper inserts records into raw_results table."""
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Lalitpur",
        "source_ids": [1]
    })
    
    assert response.status_code == 201
    job_id = response.json()["id"]
    
    # Expire session to see changes from Celery task's separate session
    db_session.expire_all()
    
    # Check raw_results
    raw_count = db_session.query(RawResult).filter(RawResult.job_id == job_id).count()
    assert raw_count == 10  # Fake scraper generates exactly 10 records


def test_cleaned_results_inserted(auth_client, db_session, mock_sleep):
    """Fake scraper inserts records into cleaned_results table."""
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Bhaktapur",
        "source_ids": [1]
    })
    
    assert response.status_code == 201
    job_id = response.json()["id"]
    
    # Expire session to see changes from Celery task's separate session
    db_session.expire_all()
    
    # Check cleaned_results
    cleaned_count = db_session.query(CleanedResult).filter(CleanedResult.job_id == job_id).count()
    assert cleaned_count == 10  # Fake scraper generates exactly 10 records
    
    # Verify fields are populated
    result = db_session.query(CleanedResult).filter(CleanedResult.job_id == job_id).first()
    assert result.name is not None
    assert result.city is not None
    assert result.dedup_key is not None
    assert result.data_completeness is not None


def test_get_job_status(auth_client, db_session, mock_sleep):
    """GET /jobs/{id}/status returns job status and result count."""
    # Create job
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Chitwan"
    })
    job_id = response.json()["id"]
    
    # Expire session to see changes from Celery task's separate session
    db_session.expire_all()
    
    # Get status
    status_resp = auth_client.get(f"/api/v1/jobs/{job_id}/status")
    assert status_resp.status_code == 200
    
    data = status_resp.json()
    assert data["status"] == "DONE"
    assert data["result_count"] == 10


@pytest.mark.skip(reason="SSE streaming not fully supported by TestClient")
def test_sse_stream_yields_events(auth_client, mock_sleep):
    """GET /jobs/{id}/stream yields SSE events until job is DONE."""
    # Create job
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Biratnagar"
    })
    job_id = response.json()["id"]
    
    # Since Celery runs synchronously, job is already DONE
    # SSE should yield final event immediately
    # Note: TestClient doesn't support streaming, so we just check the response
    stream_resp = auth_client.get(f"/api/v1/jobs/{job_id}/stream")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")


def test_paginated_results_envelope(auth_client, db_session, mock_sleep):
    """GET /jobs/{id}/results returns paginated envelope."""
    # Create job
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Birgunj"
    })
    job_id = response.json()["id"]
    
    # Get results
    results_resp = auth_client.get(f"/api/v1/jobs/{job_id}/results")
    assert results_resp.status_code == 200
    
    data = results_resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    
    assert data["total"] == 10
    assert len(data["items"]) == 10


def test_paginated_results_respects_page_size(auth_client, mock_sleep):
    """GET /jobs/{id}/results respects page_size parameter."""
    # Create job
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Butwal"
    })
    data = response.json()
    job_id = data["id"]
    
    # Get results with page_size=5
    results_resp = auth_client.get(f"/api/v1/jobs/{job_id}/results?page_size=5")
    assert results_resp.status_code == 200
    
    data = results_resp.json()
    assert len(data["items"]) == 5
    assert data["page_size"] == 5
    assert data["pages"] == 2  # 10 results / 5 per page = 2 pages


def test_rate_limit_returns_429(auth_client, mock_sleep):
    """POST /jobs rate limit returns 429 after 200 requests per hour."""
    from limiter import limiter
    limiter.reset()
    
    # Make 200 requests (the limit)
    for i in range(200):
        response = auth_client.post("/api/v1/jobs/", json={
            "category_id": 1,
            "location": f"City{i}"
        })
        assert response.status_code == 201
    
    # 201st request should be rate limited
    response = auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "TooMany"
    })
    assert response.status_code == 429


def test_admin_results_requires_admin(auth_client):
    """GET /admin/results returns 403 for non-admin users."""
    response = auth_client.get("/api/v1/admin/results")
    assert response.status_code == 403


def test_admin_results_allows_admin(admin_client, mock_sleep):
    """GET /admin/results returns 200 for admin users."""
    response = admin_client.get("/api/v1/admin/results")
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_admin_results_filters_by_status(admin_client, auth_client, db_session, mock_sleep):
    """GET /admin/results filters by status parameter."""
    # Create a job (will have PENDING results)
    auth_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Dharan"
    })
    
    # Query with status filter
    response = admin_client.get("/api/v1/admin/results?status=PENDING")
    assert response.status_code == 200
    
    data = response.json()
    # All returned items should have status PENDING
    for item in data["items"]:
        assert item["status"] == "PENDING"


def test_admin_results_sorts_by_completeness(admin_client, mock_sleep, db_session):
    """GET /admin/results sorts by data_completeness when requested."""
    from limiter import limiter
    limiter.reset()
    
    # Create a job using admin_client
    response = admin_client.post("/api/v1/jobs/", json={
        "category_id": 1,
        "location": "Hetauda"
    })
    assert response.status_code == 201
    
    # Expire session to see changes from Celery task
    db_session.expire_all()
    
    # Query with sort_by=data_completeness
    response = admin_client.get("/api/v1/admin/results?sort_by=data_completeness")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) > 0
    
    # Verify descending order
    completeness_scores = [item["data_completeness"] for item in data["items"] if item["data_completeness"] is not None]
    assert completeness_scores == sorted(completeness_scores, reverse=True)


def test_get_jobs_history(auth_client, mock_sleep, db_session):
    """GET /jobs returns paginated job history for current user."""
    from limiter import limiter
    limiter.reset()
    
    # Create 3 jobs
    for i in range(3):
        response = auth_client.post("/api/v1/jobs/", json={
            "category_id": 1,
            "location": f"City{i}"
        })
        assert response.status_code == 201
    
    # Expire session to see changes from Celery task
    db_session.expire_all()
    
    # Get job history
    response = auth_client.get("/api/v1/jobs/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
