"""Tests for app/routes/telegram.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.telegram import register


class TestTelegramRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/tg/callback/{bot_id}" in routes

    def test_tg_callback_get(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/tg/callback/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_tg_callback_post_success(self):
        """Test tg_callback_post with valid request."""
        app = FastAPI()
        register(app)

        mock_processor = MagicMock()
        mock_processor.handle_incoming_message = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_processor)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post(
            "/api/tg/callback/507f1f77bcf86cd799439011",
            json={"update_id": 123, "message": {"text": "test"}}
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_processor.handle_incoming_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_tg_callback_post_exception(self):
        """Test tg_callback_post handles exceptions gracefully."""
        app = FastAPI()
        register(app)

        mock_processor = MagicMock()
        mock_processor.handle_incoming_message = AsyncMock(side_effect=Exception("Processing error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_processor)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post(
            "/api/tg/callback/507f1f77bcf86cd799439011",
            json={"update_id": 123, "message": {"text": "test"}}
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
