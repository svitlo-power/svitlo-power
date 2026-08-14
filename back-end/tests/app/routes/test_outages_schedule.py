"""Tests for app/routes/outages_schedule.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.outages_schedule import register


class TestOutagesScheduleRoute:
    def test_register_adds_route(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/outagesSchedule/outagesSchedule/{queue}" in routes

    def test_get_outages_schedule_returns_data(self):
        """Test that get_outages_schedule returns schedule data."""
        app = FastAPI()
        register(app)

        mock_schedule = MagicMock()
        mock_schedule.model_dump.return_value = {"queue": "test", "schedule": []}

        mock_service = MagicMock()
        mock_service.get_schedule.return_value = mock_schedule

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/outagesSchedule/outagesSchedule/test_queue")
        assert response.status_code == 200
        assert response.json() == {"queue": "test", "schedule": []}

    def test_get_outages_schedule_not_found(self):
        """Test that get_outages_schedule raises 404 when schedule not found."""
        app = FastAPI()
        register(app)

        mock_service = MagicMock()
        mock_service.get_schedule.return_value = None

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/outagesSchedule/outagesSchedule/missing_queue")
        assert response.status_code == 404
        assert "No schedule found for queue missing_queue" in response.json()["detail"]
