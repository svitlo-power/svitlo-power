"""Tests for app/routes/messages.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.messages import register
from app.utils.jwt_dependencies import jwt_required


class TestMessagesRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/messages/messages" in routes
        assert "/api/messages/getChannel" in routes
        assert "/api/messages/message/{message_id}" in routes
        assert "/api/messages/getPreview" in routes
        assert "/api/messages/{message_id}/state" in routes
        assert "/api/messages" in routes
        assert "/api/messages/{message_id}" in routes

    def test_get_messages_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/messages/messages")
        assert response.status_code == 401

    def test_create_message_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/messages", json={
            "name": "Test",
            "channelId": "channel",
            "stations": [],
            "botId": "507f1f77bcf86cd799439011",
            "messageTemplate": "Hello",
            "shouldSendTemplate": "True",
            "timeoutTemplate": "300",
            "enabled": True,
            "language": "en",
        })
        assert response.status_code == 401

    def test_get_messages_success(self):
        """Test get_messages returns messages."""
        app = FastAPI()
        register(app)

        from app.models.api import MessageListResponseModel
        from beanie import PydanticObjectId
        mock_message = MessageListResponseModel(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name="Test Message",
            channel_name="test_channel",
            stations=[],
            bot_name="Test Bot",
            last_sent_time=None,
            enabled=True,
        )

        mock_messages = MagicMock()
        mock_messages.get_messages = AsyncMock(return_value=[mock_message])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/messages/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Message"

        app.dependency_overrides.clear()

    def test_get_channel_success(self):
        """Test get_channel returns channel name."""
        app = FastAPI()
        register(app)

        mock_chat_info = MagicMock()
        mock_chat_info.title = "Test Channel"
        mock_telegram = MagicMock()
        mock_telegram.get_chat_info = MagicMock(return_value=mock_chat_info)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_telegram)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages/getChannel", json={
            "channelId": "channel123",
            "botId": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["channelName"] == "Test Channel"

        app.dependency_overrides.clear()

    def test_get_channel_missing_params_returns_400(self):
        """Test get_channel returns 400 when params are missing."""
        app = FastAPI()
        register(app)

        mock_telegram = MagicMock()
        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_telegram)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages/getChannel", json={
            "channelId": "",
            "botId": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 400
        assert "channelId and botId should be specified" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_channel_exception_returns_invalid(self):
        """Test get_channel returns 'Invalid channel identifier' on exception."""
        app = FastAPI()
        register(app)

        mock_telegram = MagicMock()
        mock_telegram.get_chat_info = MagicMock(side_effect=Exception("API error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_telegram)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages/getChannel", json={
            "channelId": "channel123",
            "botId": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["channelName"] == "Invalid channel identifier"

        app.dependency_overrides.clear()

    def test_get_message_success(self):
        """Test get_message returns message."""
        app = FastAPI()
        register(app)

        from app.models.api import MessageEditResponseModel
        from beanie import PydanticObjectId
        mock_message = MessageEditResponseModel(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name="Test Message",
            channel_id="channel123",
            channel_name="Test Channel",
            stations=[],
            bot_id=PydanticObjectId("507f1f77bcf86cd799439011"),
            bot_name="Test Bot",
            last_sent_time=None,
            template_macros=None,
            message_template="Hello",
            should_send_template="True",
            timeout_template="300",
            enabled=True,
            language="en",
        )

        mock_messages = MagicMock()
        mock_messages.get_message = AsyncMock(return_value=mock_message)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/messages/message/507f1f77bcf86cd799439011")
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_get_message_preview_success(self):
        """Test get_message_preview returns preview."""
        app = FastAPI()
        register(app)

        mock_preview = MagicMock()
        mock_preview.success = True
        mock_preview.message = "Preview"
        mock_preview.should_send = True
        mock_preview.timeout = 300
        mock_preview.next_send_time = "2024-01-01T00:00:00Z"
        mock_preview.data = None

        mock_messages = MagicMock()
        mock_messages.get_message_preview = AsyncMock(return_value=mock_preview)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages/getPreview", json={
            "id": "507f1f77bcf86cd799439011",
            "name": "Test",
            "messageTemplate": "Hello",
            "timeoutTemplate": "300",
            "stations": [],
            "language": "en",
        })
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_get_message_preview_exception_returns_500(self):
        """Test get_message_preview returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_messages = MagicMock()
        mock_messages.get_message_preview = AsyncMock(side_effect=Exception("Preview error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages/getPreview", json={
            "id": "507f1f77bcf86cd799439011",
            "name": "Test",
            "messageTemplate": "Hello",
            "timeoutTemplate": "300",
            "stations": [],
            "language": "en",
        })
        assert response.status_code == 500

        app.dependency_overrides.clear()

    def test_save_message_state_success(self):
        """Test save_message_state saves state."""
        app = FastAPI()
        register(app)

        mock_messages = MagicMock()
        mock_messages.save_state = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.patch("/api/messages/507f1f77bcf86cd799439011/state", json={
            "enabled": True,
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_create_message_success(self):
        """Test create_message creates a message."""
        app = FastAPI()
        register(app)

        mock_message = MagicMock()
        mock_message.id = "507f1f77bcf86cd799439011"

        mock_messages = MagicMock()
        mock_messages.create_message = AsyncMock(return_value=mock_message)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/messages", json={
            "name": "Test",
            "channelId": "channel123",
            "stations": [],
            "botId": "507f1f77bcf86cd799439011",
            "messageTemplate": "Hello",
            "shouldSendTemplate": "True",
            "timeoutTemplate": "300",
            "enabled": True,
            "language": "en",
        })
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_update_message_success(self):
        """Test update_message updates a message."""
        app = FastAPI()
        register(app)

        mock_message = MagicMock()
        mock_message.id = "507f1f77bcf86cd799439011"

        mock_messages = MagicMock()
        mock_messages.update_message = AsyncMock(return_value=mock_message)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_messages)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/messages/507f1f77bcf86cd799439011", json={
            "name": "Test",
            "channelId": "channel123",
            "stations": [],
            "botId": "507f1f77bcf86cd799439011",
            "messageTemplate": "Hello",
            "shouldSendTemplate": "True",
            "timeoutTemplate": "300",
            "enabled": True,
            "language": "en",
        })
        assert response.status_code == 200

        app.dependency_overrides.clear()
