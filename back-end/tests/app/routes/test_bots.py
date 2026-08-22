"""Tests for app/routes/bots.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.bots import register
from app.utils.jwt_dependencies import jwt_required


class TestBotsRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/bots" in routes

    def test_get_bots_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/bots")
        assert response.status_code == 401

    def test_create_bot_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/bots", json={
            "enabled": True,
            "hookEnabled": True,
            "token": "test-token",
        })
        assert response.status_code == 401

    def test_get_bots_success(self):
        """Test get_bots returns bot list."""
        app = FastAPI()
        register(app)

        from app.models.api import BotResponse
        from beanie import PydanticObjectId
        mock_bot = BotResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name="Test Bot",
            token="token123",
            enabled=True,
            hook_enabled=True,
        )

        mock_bots_service = MagicMock()
        mock_bots_service.get_bots = AsyncMock(return_value=[mock_bot])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_bots_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/bots")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Bot"

        app.dependency_overrides.clear()

    def test_create_bot_success(self):
        """Test create_bot creates a new bot."""
        app = FastAPI()
        register(app)

        mock_bot = MagicMock()
        mock_bot.id = "507f1f77bcf86cd799439011"

        mock_bots_service = MagicMock()
        mock_bots_service.create_bot = AsyncMock(return_value=mock_bot)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_bots_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/bots", json={
            "enabled": True,
            "hookEnabled": True,
            "token": "test-token",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == "507f1f77bcf86cd799439011"

        app.dependency_overrides.clear()

    def test_update_bot_success(self):
        """Test update_bot updates a bot."""
        app = FastAPI()
        register(app)

        mock_bots_service = MagicMock()
        mock_bots_service.update_bot = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_bots_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/bots/507f1f77bcf86cd799439011", json={
            "enabled": True,
            "hookEnabled": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == "507f1f77bcf86cd799439011"

        app.dependency_overrides.clear()
