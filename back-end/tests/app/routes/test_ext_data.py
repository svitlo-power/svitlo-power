"""Tests for app/routes/ext_data.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.ext_data import register
from app.utils.jwt_dependencies import jwt_required, jwt_reporter_only


class TestExtDataRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/ext-data/list" in routes
        assert "/api/ext-data/grid-power" in routes
        assert "/api/ext-data/create" in routes
        assert "/api/ext-data/delete/{data_id}" in routes
        assert "/api/ext-data/{data_id}" in routes

    def test_get_ext_data_list_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/ext-data/list", json={
            "paging": {"page": 1, "pageSize": 10},
            "sorting": {"column": "received_at", "order": "desc"},
            "filters": [],
        })
        assert response.status_code == 401

    def test_update_grid_power_requires_reporter(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/ext-data/grid-power", json={
            "grid_power": {"state": True}
        })
        assert response.status_code == 401

    def test_get_ext_data_list_success(self):
        """Test get_ext_data_list returns data."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.get_ext_data = AsyncMock(return_value=[{"id": "123"}])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/ext-data/list", json={
            "paging": {"page": 1, "pageSize": 10},
            "sorting": {"column": "received_at", "order": "desc"},
            "filters": [],
        })
        assert response.status_code == 200
        assert response.json() == [{"id": "123"}]

        app.dependency_overrides.clear()

    def test_update_grid_power_success(self):
        """Test update_grid_power returns ok on success."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data = AsyncMock(return_value="data-id-123")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_reporter_only] = lambda: {"sub": "reporter_user"}

        client = TestClient(app)
        response = client.post("/api/ext-data/grid-power", json={
            "grid_power": {"state": True}
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        app.dependency_overrides.clear()

    def test_update_grid_power_data_id_none_returns_500(self):
        """Test update_grid_power returns 500 when data_id is None."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_reporter_only] = lambda: {"sub": "reporter_user"}

        client = TestClient(app)
        response = client.post("/api/ext-data/grid-power", json={
            "grid_power": {"state": True}
        })
        assert response.status_code == 500
        assert "Failed to update data state" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_update_grid_power_exception_returns_500(self):
        """Test update_grid_power returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data = AsyncMock(side_effect=Exception("DB error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_reporter_only] = lambda: {"sub": "reporter_user"}

        client = TestClient(app)
        response = client.post("/api/ext-data/grid-power", json={
            "grid_power": {"state": True}
        })
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_create_ext_data_success(self):
        """Test create_ext_data returns ok with id."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data_by_user_id = AsyncMock(return_value="new-data-id")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/ext-data/create", json={
            "user_id": "507f1f77bcf86cd799439011",
            "grid_state": True,
            "received_at": "2024-01-01T00:00:00Z",
        })
        assert response.status_code == 201
        assert response.json()["status"] == "ok"
        assert response.json()["id"] == "new-data-id"

        app.dependency_overrides.clear()

    def test_create_ext_data_data_id_none_returns_500(self):
        """Test create_ext_data returns 500 when data_id is None."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data_by_user_id = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/ext-data/create", json={
            "user_id": "507f1f77bcf86cd799439011",
            "grid_state": True,
        })
        assert response.status_code == 500
        assert "Failed to create ext_data" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_create_ext_data_exception_returns_500(self):
        """Test create_ext_data returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.add_ext_data_by_user_id = AsyncMock(side_effect=Exception("DB error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/ext-data/create", json={
            "user_id": "507f1f77bcf86cd799439011",
            "grid_state": True,
        })
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_delete_ext_data_success(self):
        """Test delete_ext_data returns ok on success."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.delete_ext_data = AsyncMock(return_value=True)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/ext-data/delete/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        app.dependency_overrides.clear()

    def test_delete_ext_data_not_found_returns_404(self):
        """Test delete_ext_data returns 404 when not found."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.delete_ext_data = AsyncMock(return_value=False)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/ext-data/delete/507f1f77bcf86cd799439011")
        assert response.status_code == 404
        assert "Ext_data not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_delete_ext_data_exception_returns_500(self):
        """Test delete_ext_data returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.delete_ext_data = AsyncMock(side_effect=Exception("DB error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/ext-data/delete/507f1f77bcf86cd799439011")
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_ext_data_by_id_success(self):
        """Test get_ext_data_by_id returns data."""
        app = FastAPI()
        register(app)

        mock_data = MagicMock()
        mock_data.id = "507f1f77bcf86cd799439011"
        mock_data.user_id = "507f1f77bcf86cd799439011"
        mock_data.grid_state = True
        mock_data.received_at = MagicMock()
        mock_data.received_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00Z")
        mock_data.user = MagicMock()
        mock_data.user.name = "testuser"

        mock_ext_data = MagicMock()
        mock_ext_data.get_by_id = AsyncMock(return_value=mock_data)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/ext-data/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["grid_state"] is True

        app.dependency_overrides.clear()

    def test_get_ext_data_by_id_not_found_returns_404(self):
        """Test get_ext_data_by_id returns 404 when not found."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.get_by_id = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/ext-data/507f1f77bcf86cd799439011")
        assert response.status_code == 404
        assert "Ext_data not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_ext_data_by_id_exception_returns_500(self):
        """Test get_ext_data_by_id returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_data = MagicMock()
        mock_ext_data.get_by_id = AsyncMock(side_effect=Exception("DB error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/ext-data/507f1f77bcf86cd799439011")
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_ext_data_by_id_no_user(self):
        """Test get_ext_data_by_id when user is None."""
        app = FastAPI()
        register(app)

        mock_data = MagicMock()
        mock_data.id = "507f1f77bcf86cd799439011"
        mock_data.user_id = "507f1f77bcf86cd799439011"
        mock_data.grid_state = True
        mock_data.received_at = MagicMock()
        mock_data.received_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00Z")
        mock_data.user = None

        mock_ext_data = MagicMock()
        mock_ext_data.get_by_id = AsyncMock(return_value=mock_data)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/ext-data/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is None

        app.dependency_overrides.clear()

    def test_get_ext_data_by_id_no_received_at(self):
        """Test get_ext_data_by_id when received_at is None."""
        app = FastAPI()
        register(app)

        mock_data = MagicMock()
        mock_data.id = "507f1f77bcf86cd799439011"
        mock_data.user_id = "507f1f77bcf86cd799439011"
        mock_data.grid_state = True
        mock_data.received_at = None
        mock_data.user = MagicMock()
        mock_data.user.name = "testuser"

        mock_ext_data = MagicMock()
        mock_ext_data.get_by_id = AsyncMock(return_value=mock_data)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_data)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/ext-data/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["received_at"] is None

        app.dependency_overrides.clear()
