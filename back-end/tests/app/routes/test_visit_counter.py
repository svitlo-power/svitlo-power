"""Tests for app/routes/visit_counter.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.visit_counter import register


class TestVisitCounterRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/visit/add" in routes
        assert "/api/visit/stats" in routes

    def test_visit_add_success(self):
        """Test visit endpoint adds a visit."""
        app = FastAPI()
        register(app)

        mock_visit_counter = MagicMock()
        mock_visit_counter.add_visit = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_visit_counter)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/visit/add?type=page_view&date=2024-01-01")
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_visit_counter.add_visit.assert_called_once_with("page_view", "2024-01-01")

    def test_visit_add_no_params(self):
        """Test visit endpoint with no params."""
        app = FastAPI()
        register(app)

        mock_visit_counter = MagicMock()
        mock_visit_counter.add_visit = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_visit_counter)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/visit/add")
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_visit_counter.add_visit.assert_called_once_with(None, None)

    def test_visit_stats_success(self):
        """Test stats endpoint returns today's stats."""
        app = FastAPI()
        register(app)

        mock_stats = MagicMock()
        mock_stats.model_dump.return_value = {"views": 100, "unique_visitors": 50}

        mock_visit_counter = MagicMock()
        mock_visit_counter.get_today_stats = AsyncMock(return_value=mock_stats)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_visit_counter)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/visit/stats")
        assert response.status_code == 200
