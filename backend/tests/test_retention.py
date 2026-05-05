"""
Tests for data retention task (auto-purge old raw_results).
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from tasks.retention_task import purge_old_raw_results


class TestRetentionTask:
    """Test suite for raw_results retention/purge task."""
    
    def test_purge_deletes_old_raw_results(self, db_session, test_user):
        """Test that task deletes raw_results older than 90 days."""
        # Create a job first (required for foreign key)
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create old raw_result (91 days old)
        old_date = datetime.utcnow() - timedelta(days=91)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data"}', :old_date)
            """),
            {"job_id": job_id, "old_date": old_date}
        )
        
        # Create recent raw_result (30 days old)
        recent_date = datetime.utcnow() - timedelta(days=30)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data2"}', :recent_date)
            """),
            {"job_id": job_id, "recent_date": recent_date}
        )
        db_session.commit()
        
        # Run purge task
        result = purge_old_raw_results(db_session)
        
        # Verify old record deleted, recent record kept
        assert result["success"] is True
        assert result["deleted_count"] >= 1
        
        remaining = db_session.execute(
            text("SELECT COUNT(*) FROM raw_results WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).scalar()
        assert remaining == 1
    
    def test_purge_does_not_delete_cleaned_results(self, db_session, test_user):
        """Test that task does NOT delete cleaned_results or validated_results."""
        # Create a job first
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create old raw_result
        old_date = datetime.utcnow() - timedelta(days=91)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data"}', :old_date)
            """),
            {"job_id": job_id, "old_date": old_date}
        )
        
        # Create old cleaned_result
        db_session.execute(
            text("""
                INSERT INTO cleaned_results (
                    job_id, source_id, name, category_id, 
                    data_completeness, dedup_key, created_at
                )
                VALUES (:job_id, 1, 'Test Business', 1, 0.5, 'test-key', :old_date)
            """),
            {"job_id": job_id, "old_date": old_date}
        )
        db_session.commit()
        
        # Run purge task
        result = purge_old_raw_results(db_session)
        
        # Verify raw_result deleted but cleaned_result kept
        assert result["success"] is True
        
        cleaned_count = db_session.execute(
            text("SELECT COUNT(*) FROM cleaned_results WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).scalar()
        assert cleaned_count == 1
    
    def test_purge_logs_deletion_count(self, db_session, test_user):
        """Test that task logs structured event with deletion count."""
        # Create a job first
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create old raw_result
        old_date = datetime.utcnow() - timedelta(days=91)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data"}', :old_date)
            """),
            {"job_id": job_id, "old_date": old_date}
        )
        db_session.commit()
        
        # Run purge task
        result = purge_old_raw_results(db_session)
        
        # Verify logging
        assert result["success"] is True
        assert "deleted_count" in result
        assert "duration_seconds" in result
    
    def test_purge_handles_db_errors_gracefully(self, db_session, monkeypatch):
        """Test that task handles DB errors without crashing Beat scheduler."""
        # Mock the execute method to raise an error
        original_execute = db_session.execute
        
        def mock_execute(*args, **kwargs):
            raise Exception("Database connection lost")
        
        monkeypatch.setattr(db_session, "execute", mock_execute)
        
        # Run purge task - should not raise exception
        result = purge_old_raw_results(db_session)
        
        # Verify error handled gracefully
        assert result["success"] is False
        assert "error" in result
    
    def test_purge_skips_when_no_old_records(self, db_session, test_user):
        """Test that task completes successfully when no old records exist."""
        # Create a job first
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create only recent raw_results
        recent_date = datetime.utcnow() - timedelta(days=30)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data"}', :recent_date)
            """),
            {"job_id": job_id, "recent_date": recent_date}
        )
        db_session.commit()
        
        # Count before purge
        count_before = db_session.execute(
            text("SELECT COUNT(*) FROM raw_results WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).scalar()
        
        # Run purge task
        result = purge_old_raw_results(db_session)
        
        # Verify no deletions for this job, task succeeds
        assert result["success"] is True
        
        remaining = db_session.execute(
            text("SELECT COUNT(*) FROM raw_results WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).scalar()
        assert remaining == count_before
    
    def test_purge_respects_retention_days_config(self, db_session, test_user, monkeypatch):
        """Test that task respects RAW_RESULTS_RETENTION_DAYS config."""
        from config import settings
        
        # Set retention to 30 days
        monkeypatch.setattr(settings, 'RAW_RESULTS_RETENTION_DAYS', 30)
        
        # Create a job first
        job_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO scrape_jobs (id, user_id, category_id, location, status, created_at)
                VALUES (:job_id, :user_id, 1, 'Kathmandu', 'DONE', NOW())
            """),
            {"job_id": job_id, "user_id": test_user.id}
        )
        
        # Create raw_result 31 days old (should be deleted)
        old_date = datetime.utcnow() - timedelta(days=31)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data"}', :old_date)
            """),
            {"job_id": job_id, "old_date": old_date}
        )
        
        # Create raw_result 29 days old (should be kept)
        recent_date = datetime.utcnow() - timedelta(days=29)
        db_session.execute(
            text("""
                INSERT INTO raw_results (job_id, source_id, raw_data, scraped_at)
                VALUES (:job_id, 1, '{"test": "data2"}', :recent_date)
            """),
            {"job_id": job_id, "recent_date": recent_date}
        )
        db_session.commit()
        
        # Run purge task
        result = purge_old_raw_results(db_session)
        
        # Verify only 31-day-old record deleted
        assert result["success"] is True
        assert result["retention_days"] == 30
        
        # Check that 29-day-old record still exists
        remaining = db_session.execute(
            text("SELECT COUNT(*) FROM raw_results WHERE job_id = :job_id"),
            {"job_id": job_id}
        ).scalar()
        assert remaining == 1
