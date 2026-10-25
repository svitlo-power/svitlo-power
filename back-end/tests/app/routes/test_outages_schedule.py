"""Tests for app/routes/outages_schedule.py."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from yarl import URL

from app.routes.outages_schedule import register
from app.utils.jwt_dependencies import get_current_jwt


class TestOutagesScheduleRoute:
    def test_register_adds_route(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/outagesSchedule/outagesSchedule/{queue}" in routes
        assert "/api/outagesSchedule/regions" in routes
        assert "/api/outagesSchedule/providers/{region_name:path}" in routes
        assert "/api/outagesSchedule/queues/{region_id}/{dso_id}" in routes

    def test_discovery_endpoints_return_yasno_options(self):
        app = FastAPI()
        register(app)

        mock_service = MagicMock()
        mock_service.fetch_regions = AsyncMock(return_value=[{
            "id": 25,
            "value": "Kyiv",
            "label": "Kyiv",
            "dsos": [{"id": 902, "name": "Yasno"}],
        }])
        mock_service.fetch_providers_for_region = AsyncMock(
            return_value=[{"id": 902, "name": "Yasno"}],
        )
        mock_service.fetch_queues = AsyncMock(return_value=["1.1", "1.2"])
        app.state.injector = MagicMock(get=MagicMock(return_value=mock_service))
        app.dependency_overrides[get_current_jwt] = lambda: {"sub": "test-user"}

        client = TestClient(app)
        assert client.get("/api/outagesSchedule/regions").json()[0]["value"] == "Kyiv"
        assert client.get("/api/outagesSchedule/providers/Kyiv").json() == [
            {"id": 902, "name": "Yasno"},
        ]
        assert client.get("/api/outagesSchedule/queues/25/902").json() == ["1.1", "1.2"]
        mock_service.fetch_providers_for_region.assert_awaited_with("Kyiv")
        app.dependency_overrides.clear()

    def test_provider_endpoint_accepts_region_names_containing_slashes(self):
        app = FastAPI()
        register(app)
        mock_service = MagicMock()
        mock_service.fetch_providers_for_region = AsyncMock(return_value=[])
        app.state.injector = MagicMock(get=MagicMock(return_value=mock_service))
        app.dependency_overrides[get_current_jwt] = lambda: {"sub": "test-user"}

        response = TestClient(app).get("/api/outagesSchedule/providers/Region%2FName")

        assert response.status_code == 200
        mock_service.fetch_providers_for_region.assert_awaited_once_with("Region/Name")
        app.dependency_overrides.clear()

    def test_discovery_endpoints_require_authentication(self):
        app = FastAPI()
        register(app)

        response = TestClient(app).get("/api/outagesSchedule/regions")

        assert response.status_code in (401, 403)

    @pytest.mark.parametrize(
        ("method", "path", "upstream_error", "status_code"),
        [
            (method, path, error, status_code)
            for method, path in [
                ("fetch_regions", "/api/outagesSchedule/regions"),
                ("fetch_providers_for_region", "/api/outagesSchedule/providers/Kyiv"),
                ("fetch_queues", "/api/outagesSchedule/queues/25/902"),
            ]
            for error, status_code in [
                (aiohttp.ClientResponseError(
                    request_info=MagicMock(real_url=URL("https://yasno.example")),
                    history=(),
                    status=404,
                ), 404),
                (aiohttp.ClientResponseError(
                    request_info=MagicMock(real_url=URL("https://yasno.example")),
                    history=(),
                    status=503,
                ), 502),
                (aiohttp.ClientError("connection failed"), 502),
                (asyncio.TimeoutError(), 502),
                (ValueError("invalid response"), 502),
            ]
        ],
    )
    def test_discovery_endpoints_map_upstream_errors(
        self, method, path, upstream_error, status_code,
    ):
        app = FastAPI()
        register(app)
        mock_service = MagicMock()
        setattr(mock_service, method, AsyncMock(side_effect=upstream_error))
        app.state.injector = MagicMock(get=MagicMock(return_value=mock_service))
        app.dependency_overrides[get_current_jwt] = lambda: {"sub": "test-user"}

        response = TestClient(app).get(path)

        assert response.status_code == status_code
        app.dependency_overrides.clear()

    def test_provider_endpoint_maps_unknown_region_to_not_found(self):
        app = FastAPI()
        register(app)
        mock_service = MagicMock()
        mock_service.fetch_providers_for_region = AsyncMock(
            side_effect=KeyError("Unknown YASNO region: Missing"),
        )
        app.state.injector = MagicMock(get=MagicMock(return_value=mock_service))
        app.dependency_overrides[get_current_jwt] = lambda: {"sub": "test-user"}

        response = TestClient(app).get("/api/outagesSchedule/providers/Missing")

        assert response.status_code == 404
        assert "Unknown YASNO region: Missing" in response.json()["detail"]
        app.dependency_overrides.clear()

    def test_get_outages_schedule_returns_data(self):
        """Test that get_outages_schedule returns schedule data."""
        app = FastAPI()
        register(app)

        # Create a mock SchedulesResponse with root containing the queue
        mock_unit_schedule = MagicMock()
        mock_unit_schedule.model_dump.return_value = {"days": [{"start": 0, "end": 120, "type": "Definite"}]}

        mock_schedule = MagicMock()
        mock_schedule.root = {"test_queue": mock_unit_schedule}

        mock_service = MagicMock()
        mock_service.get_schedule_async = AsyncMock(return_value=mock_schedule)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/outagesSchedule/outagesSchedule/test_queue")
        assert response.status_code == 200
        assert response.json() == {"days": [{"start": 0, "end": 120, "type": "Definite"}]}

    def test_get_outages_schedule_not_found(self):
        """Test that get_outages_schedule raises 404 when schedule not found."""
        app = FastAPI()
        register(app)

        mock_service = MagicMock()
        mock_service.get_schedule_async = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/outagesSchedule/outagesSchedule/missing_queue")
        assert response.status_code == 404
        assert "No schedule found for queue missing_queue" in response.json()["detail"]