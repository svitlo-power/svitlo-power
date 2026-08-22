"""Tests for app/routes/users.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.users import register
from app.utils.jwt_dependencies import jwt_required


class TestUsersRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/users/users" in routes
        assert "/api/users/login-history/{user_id}" in routes
        assert "/api/users/save" in routes
        assert "/api/users/delete/{user_id}" in routes
        assert "/api/users/generate-token/{user_id}" in routes
        assert "/api/users/delete-token/{user_id}" in routes

    def test_get_users_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/users/users")
        assert response.status_code == 401

    def test_save_user_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.put("/api/users/save", json={"id": "507f1f77bcf86cd799439011", "name": "test"})
        assert response.status_code == 401

    def test_get_users_success(self):
        """Test get_users returns users excluding current user."""
        app = FastAPI()
        register(app)

        from app.models.api import UserListResponseModel
        from beanie import PydanticObjectId
        mock_user1 = UserListResponseModel(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name="user1",
            is_active=True,
            is_reporter=False,
            api_key=None,
            report_mode=None,
        )
        mock_user2 = UserListResponseModel(
            id=PydanticObjectId("507f1f77bcf86cd799439012"),
            name="testuser",
            is_active=True,
            is_reporter=False,
            api_key=None,
            report_mode=None,
        )

        mock_users_service = MagicMock()
        mock_users_service.get_users = AsyncMock(return_value=[mock_user1, mock_user2])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/users/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "user1"

        app.dependency_overrides.clear()

    def test_get_login_history_success(self):
        """Test get_login_history returns login history."""
        app = FastAPI()
        register(app)

        from app.models.api import LoginHistoryItemResponse
        from beanie import PydanticObjectId
        from datetime import datetime, timezone
        mock_history = LoginHistoryItemResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            login_time=datetime.now(timezone.utc),
            ip_address="127.0.0.1",
        )

        mock_users_service = MagicMock()
        mock_users_service.get_login_history = AsyncMock(return_value=[mock_history])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/users/login-history/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        app.dependency_overrides.clear()

    def test_save_user_success(self):
        """Test save_user creates/updates user."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.save_user = AsyncMock(return_value=("507f1f77bcf86cd799439011", "reset-token"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/users/save", json={
            "id": "507f1f77bcf86cd799439011",
            "name": "testuser",
            "isActive": True,
            "isReporter": False,
            "reportMode": "event",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == "507f1f77bcf86cd799439011"
        assert data["resetToken"] == "reset-token"

        app.dependency_overrides.clear()

    def test_save_user_defaults(self):
        """Test save_user uses default values."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.save_user = AsyncMock(return_value=("507f1f77bcf86cd799439011", None))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/users/save", json={
            "id": "507f1f77bcf86cd799439011",
            "name": "testuser",
        })
        assert response.status_code == 200
        mock_users_service.save_user.assert_called_once()

        app.dependency_overrides.clear()

    def test_delete_user_success(self):
        """Test delete_user returns success."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.delete_user = AsyncMock(return_value=True)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/users/delete/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_delete_user_not_found_returns_404(self):
        """Test delete_user returns 404 when user not found."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.delete_user = AsyncMock(return_value=False)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/users/delete/507f1f77bcf86cd799439011")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_generate_token_success(self):
        """Test generate_token returns token."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.create_reporter_token = AsyncMock(return_value="generated-token")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/users/generate-token/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["token"] == "generated-token"

        app.dependency_overrides.clear()

    def test_generate_token_failure_returns_500(self):
        """Test generate_token returns 500 when token is None."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.create_reporter_token = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/users/generate-token/507f1f77bcf86cd799439011")
        assert response.status_code == 500
        assert "Failed to generate token" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_delete_token_success(self):
        """Test delete_token returns success."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.delete_reporter_token = AsyncMock(return_value=True)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/users/delete-token/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_delete_token_failure(self):
        """Test delete_token returns success=False when deletion fails."""
        app = FastAPI()
        register(app)

        mock_users_service = MagicMock()
        mock_users_service.delete_reporter_token = AsyncMock(return_value=False)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_users_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/users/delete-token/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["success"] is False

        app.dependency_overrides.clear()
