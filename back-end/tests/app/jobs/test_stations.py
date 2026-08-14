"""Tests for app/jobs/stations.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.jobs.stations import register
from app.services import StationConnectionsService, StationsService


class TestRegister:
    def test_register_adds_check_deye_status_job(self):
        """Test that register adds check_deye_status job to scheduler."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = []

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called for check_deye_status
        calls = scheduler.add_job.call_args_list
        assert len(calls) >= 1
        check_deye_call = calls[0]
        assert check_deye_call[1]["id"] == "check_deye_status"
        assert check_deye_call[1]["trigger"] == "interval"
        assert check_deye_call[1]["seconds"] == 180

    def test_register_adds_sync_deye_stations_job(self):
        """Test that register adds sync_deye_stations job to scheduler."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = []

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called for sync_deye_stations
        calls = scheduler.add_job.call_args_list
        assert len(calls) >= 2
        sync_stations_call = calls[1]
        assert sync_stations_call[1]["id"] == "sync_deye_stations"
        assert sync_stations_call[1]["trigger"] == "cron"
        assert sync_stations_call[1]["hour"] == "*/3"
        assert sync_stations_call[1]["minute"] == "0"
        assert sync_stations_call[1]["second"] == "0"

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = []

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        injector.get.assert_called()

    def test_check_deye_status_with_sync_on_poll_connections(self):
        """Test check_deye_status with connections that have sync_stations_on_poll=True."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_conn1 = MagicMock()
        mock_conn1.id = "conn1"
        mock_conn1.sync_stations_on_poll = True

        mock_conn2 = MagicMock()
        mock_conn2.id = "conn2"
        mock_conn2.sync_stations_on_poll = False

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = [mock_conn1, mock_conn2]

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the check_deye_status job function and execute it
        calls = scheduler.add_job.call_args_list
        check_deye_call = calls[0]
        job_func = check_deye_call[1]["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify sync_stations was called with the correct connection IDs
        mock_stations.sync_stations.assert_called_once_with(["conn1"])

    def test_check_deye_status_without_sync_on_poll_connections(self):
        """Test check_deye_status with no connections that have sync_stations_on_poll=True."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_conn1 = MagicMock()
        mock_conn1.id = "conn1"
        mock_conn1.sync_stations_on_poll = False

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = [mock_conn1]

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the check_deye_status job function and execute it
        calls = scheduler.add_job.call_args_list
        check_deye_call = calls[0]
        job_func = check_deye_call[1]["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify sync_stations_data was called
        mock_stations.sync_stations_data.assert_called_once()

    def test_sync_stations_scheduled_with_connections(self):
        """Test sync_stations_scheduled with connections that don't have sync_stations_on_poll."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_conn1 = MagicMock()
        mock_conn1.id = "conn1"
        mock_conn1.sync_stations_on_poll = False

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = [mock_conn1]

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the sync_deye_stations job function and execute it
        calls = scheduler.add_job.call_args_list
        sync_stations_call = calls[1]
        job_func = sync_stations_call[1]["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify sync_stations was called with the correct connection IDs
        mock_stations.sync_stations.assert_called_once_with(["conn1"])

    def test_sync_stations_scheduled_without_connections(self):
        """Test sync_stations_scheduled with no connections."""
        settings = MagicMock()
        settings.DEYE_FETCH_INTERVAL = 180
        injector = MagicMock()
        scheduler = MagicMock()

        mock_connections = MagicMock()
        mock_connections.get_connections.return_value = []

        mock_stations = MagicMock()
        mock_stations.sync_stations = AsyncMock()
        mock_stations.sync_stations_data = AsyncMock()

        def get_side_effect(cls):
            if cls is StationConnectionsService:
                return mock_connections
            if cls is StationsService:
                return mock_stations
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the sync_deye_stations job function and execute it
        calls = scheduler.add_job.call_args_list
        sync_stations_call = calls[1]
        job_func = sync_stations_call[1]["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify sync_stations was NOT called (no connections)
        mock_stations.sync_stations.assert_not_called()