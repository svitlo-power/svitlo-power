"""Tests for app/routes/app_info.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.app_info import register


class TestAppInfoRoute:
    def test_register_adds_route(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/app/info" in routes

    @pytest.mark.asyncio
    async def test_get_app_info_request_error(self):
        app = FastAPI()
        register(app)

        with patch("app.routes.app_info.httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get = MagicMock(side_effect=Exception("Connection error"))
            mock_client_cls.return_value = mock_client

            client = TestClient(app)
            response = client.get("/api/app/info")
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_app_info_success(self):
        """Test get_app_info returns app info on success."""
        app = FastAPI()
        register(app)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "fields": {
                "updateUrl": {"stringValue": "https://example.com/update"},
                "ver": {"stringValue": "1.2.3"},
            }
        })

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.routes.app_info.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app)
            response = client.get("/api/app/info")
            assert response.status_code == 200
            data = response.json()
            assert data["updateUrl"] == "https://example.com/update"
            assert data["version"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_get_app_info_http_error(self):
        """Test get_app_info returns 500 on httpx.RequestError."""
        app = FastAPI()
        register(app)

        import httpx

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.routes.app_info.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app)
            response = client.get("/api/app/info")
            assert response.status_code == 500
            assert "Failed to fetch app information" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_app_info_generic_exception(self):
        """Test get_app_info returns 500 on generic exception."""
        app = FastAPI()
        register(app)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Unexpected error"))
        mock_response.json = MagicMock(return_value={})

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.routes.app_info.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app)
            response = client.get("/api/app/info")
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_app_info_empty_fields(self):
        """Test get_app_info handles empty fields."""
        app = FastAPI()
        register(app)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"fields": {}})

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.routes.app_info.httpx.AsyncClient", return_value=mock_client):
            client = TestClient(app)
            response = client.get("/api/app/info")
            assert response.status_code == 200
            data = response.json()
            assert data["updateUrl"] == ""
            assert data["version"] == ""
