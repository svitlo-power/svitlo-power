"""Tests for app/routes/lookup.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.lookup import register
from app.utils.jwt_dependencies import jwt_required


class TestLookupRoute:
    def test_register_adds_route(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/lookup/{lookup_name}" in routes

    def test_get_lookup_values_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/lookup/test")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_lookup_values_returns_data(self):
        """Test that get_lookup_values returns data from the service."""
        app = FastAPI()
        register(app)

        mock_lookups = MagicMock()
        mock_lookups.get_lookup_values = AsyncMock(return_value={"key": "value"})

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_lookups)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"user_id": "test"}

        client = TestClient(app)
        response = client.get("/api/lookup/test")
        assert response.status_code == 200
        app.dependency_overrides.clear()
