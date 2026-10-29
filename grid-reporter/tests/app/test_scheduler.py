"""Tests for grid-reporter scheduler."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.scheduler import create_scheduler, create_client_job, setup_scheduler_jobs
from app.client_worker import ClientWorker
from app.config import ClientConfig
from app.settings import Settings
from shared.features import feature_flags, FeatureFlag


class TestScheduler:
    def test_create_scheduler(self):
        """Test that create_scheduler returns an AsyncIOScheduler."""
        scheduler = create_scheduler()
        assert scheduler is not None
        assert str(scheduler.timezone) == "UTC"

    def test_create_client_job(self):
        """Test that create_client_job adds a job to scheduler."""
        scheduler = MagicMock()
        
        # Create mock client worker
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        
        mock_deye_client = MagicMock()
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_settings = MagicMock(spec=Settings)
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        create_client_job(scheduler, worker, 240, "test_client")
        
        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "client_poll_test_client"
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["seconds"] == 240
        assert call_kwargs["max_instances"] == 1
        assert call_kwargs["coalesce"] is True
        assert call_kwargs["misfire_grace_time"] == 30

    def test_create_client_job_removes_existing(self):
        """Test that create_client_job removes existing job with same ID."""
        scheduler = MagicMock()
        scheduler.get_job.return_value = MagicMock()
        
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        
        mock_deye_client = MagicMock()
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_settings = MagicMock(spec=Settings)
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        create_client_job(scheduler, worker, 240, "test_client")
        
        # Verify existing job was removed
        scheduler.remove_job.assert_called_once_with("client_poll_test_client")


class TestSchedulerMetrics:
    def test_scheduler_metrics_registered(self):
        """Test that scheduler metrics are registered on scheduler creation."""
        from app.scheduler_metrics import register_scheduler_metrics
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from shared.metrics import JOB_EXECUTION_DURATION, JOB_EXECUTION_SUCCESS, JOB_EXECUTION_FAILURE
        
        scheduler = AsyncIOScheduler()
        register_scheduler_metrics(scheduler)
        
        # Verify listener was added
        assert len(scheduler._listeners) > 0