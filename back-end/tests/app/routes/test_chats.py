"""Tests for app/routes/chats.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.chats import register
from app.utils.jwt_dependencies import jwt_required


class TestChatsRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/chats/allowedChats" in routes
        assert "/api/chats/chatRequests" in routes
        assert "/api/chats/approve" in routes
        assert "/api/chats/reject" in routes
        assert "/api/chats/disallow" in routes

    def test_get_chats_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/chats/allowedChats")
        assert response.status_code == 401

    def test_get_chat_requests_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/chats/chatRequests")
        assert response.status_code == 401

    def test_get_chats_success(self):
        """Test get_chats returns allowed chats."""
        app = FastAPI()
        register(app)

        mock_chat = MagicMock()
        mock_chat.id = "507f1f77bcf86cd799439011"
        mock_chat.chat_id = "chat123"
        mock_chat.chat_name = "Test Chat"
        mock_chat.bot_id = "507f1f77bcf86cd799439011"
        mock_chat.bot_name = "Test Bot"
        mock_chat.approve_date = "2024-01-01T00:00:00Z"

        mock_chats_service = MagicMock()
        mock_chats_service.get_chats = AsyncMock(return_value=[mock_chat])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_chats_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/chats/allowedChats")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        app.dependency_overrides.clear()

    def test_get_chat_requests_success(self):
        """Test get_chat_requests returns chat requests."""
        app = FastAPI()
        register(app)

        mock_request = MagicMock()
        mock_request.id = "507f1f77bcf86cd799439011"
        mock_request.chat_id = "chat123"
        mock_request.chat_name = "Test Chat"
        mock_request.bot_id = "507f1f77bcf86cd799439011"
        mock_request.bot_name = "Test Bot"
        mock_request.request_date = "2024-01-01T00:00:00Z"

        mock_chats_service = MagicMock()
        mock_chats_service.get_chat_requests = AsyncMock(return_value=[mock_request])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_chats_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/chats/chatRequests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        app.dependency_overrides.clear()

    def test_approve_chat_request_success(self):
        """Test approve_chat_request approves a chat."""
        app = FastAPI()
        register(app)

        mock_chats_service = MagicMock()
        mock_chats_service.approve_chat_request = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_chats_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.patch("/api/chats/approve", json={
            "id": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        app.dependency_overrides.clear()

    def test_reject_chat_request_success(self):
        """Test reject_chat_request rejects a chat."""
        app = FastAPI()
        register(app)

        mock_chats_service = MagicMock()
        mock_chats_service.reject_chat_request = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_chats_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.patch("/api/chats/reject", json={
            "id": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        app.dependency_overrides.clear()

    def test_disallow_chat_success(self):
        """Test disallow_chat disallows a chat."""
        app = FastAPI()
        register(app)

        mock_chats_service = MagicMock()
        mock_chats_service.disallow_chat = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_chats_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.patch("/api/chats/disallow", json={
            "id": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        app.dependency_overrides.clear()
