"""Tests for app/routes/authorization.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.authorization import register
from app.utils.jwt_dependencies import jwt_required, jwt_refresh_required


class TestAuthorizationRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/auth/login" in routes
        assert "/api/auth/profile" in routes
        assert "/api/auth/saveProfile" in routes
        assert "/api/auth/startPasswordChange" in routes
        assert "/api/auth/cancelPasswordChange" in routes
        assert "/api/auth/changePassword" in routes
        assert "/api/auth/refresh" in routes

    def test_profile_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/auth/profile")
        assert response.status_code == 401

    def test_login_success(self):
        """Test login returns tokens on success."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.login = AsyncMock(return_value=("access-token", "refresh-token"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/auth/login", json={
            "userName": "testuser",
            "password": "testpass",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["accessToken"] == "access-token"
        assert data["refreshToken"] == "refresh-token"

    def test_login_value_error_returns_401(self):
        """Test login returns 401 on ValueError."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.login = AsyncMock(side_effect=ValueError("Invalid credentials"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/auth/login", json={
            "userName": "testuser",
            "password": "wrongpass",
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_profile_success(self):
        """Test profile returns user info when JWT is valid."""
        app = FastAPI()
        register(app)

        mock_user = MagicMock()
        mock_user.name = "testuser"
        mock_user.id = "507f1f77bcf86cd799439011"

        mock_auth = MagicMock()
        mock_auth.get_user = AsyncMock(return_value=mock_user)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/auth/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["userName"] == "testuser"
        assert data["userId"] == "507f1f77bcf86cd799439011"

        app.dependency_overrides.clear()

    def test_profile_user_not_found_returns_400(self):
        """Test profile returns 400 when user is not found."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.get_user = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/auth/profile")
        assert response.status_code == 400
        assert "Cannot find user" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_save_profile_success(self):
        """Test saveProfile calls rename_user."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.rename_user = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/saveProfile", json={
            "userId": "507f1f77bcf86cd799439011",
            "userName": "newname",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_auth.rename_user.assert_called_once()

        app.dependency_overrides.clear()

    def test_start_password_change_success(self):
        """Test startPasswordChange returns reset token."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.start_change_password = AsyncMock(return_value="reset-token-123")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/startPasswordChange", json={
            "userName": "testuser",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["resetToken"] == "reset-token-123"

        app.dependency_overrides.clear()

    def test_start_password_change_value_error_returns_500(self):
        """Test startPasswordChange returns 500 on ValueError."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.start_change_password = AsyncMock(side_effect=ValueError("User not found"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/startPasswordChange", json={
            "userName": "testuser",
        })
        assert response.status_code == 500
        assert "Error changing password" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_cancel_password_change_success(self):
        """Test cancelPasswordChange succeeds."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.cancel_change_password = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/cancelPasswordChange", json={
            "userName": "testuser",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_cancel_password_change_value_error_returns_500(self):
        """Test cancelPasswordChange returns 500 on ValueError."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.cancel_change_password = AsyncMock(side_effect=ValueError("No pending change"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/cancelPasswordChange", json={
            "userName": "testuser",
        })
        assert response.status_code == 500
        assert "Error changing password" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_change_password_success(self):
        """Test changePassword succeeds."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.change_password = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/auth/changePassword", json={
            "resetToken": "token123",
            "newPassword": "newpass123",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_change_password_missing_fields_returns_400(self):
        """Test changePassword returns 400 when fields are missing."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.change_password = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/auth/changePassword", json={
            "resetToken": "",
            "newPassword": "",
        })
        assert response.status_code == 400
        assert "Invalid request" in response.json()["detail"]

    def test_change_password_value_error_returns_401(self):
        """Test changePassword returns 401 on ValueError."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.change_password = AsyncMock(side_effect=ValueError("Invalid token"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/auth/changePassword", json={
            "resetToken": "token123",
            "newPassword": "newpass123",
        })
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_refresh_success(self):
        """Test refresh returns new access token."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.refresh_token = AsyncMock(return_value="new-access-token")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_refresh_required] = lambda: {"sub": "testuser", "refresh_token": "old-refresh"}

        client = TestClient(app)
        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["accessToken"] == "new-access-token"
        assert data["refreshToken"] == "old-refresh"

        app.dependency_overrides.clear()

    def test_refresh_without_refresh_token_in_claims(self):
        """Test refresh when refresh_token is not in claims."""
        app = FastAPI()
        register(app)

        mock_auth = MagicMock()
        mock_auth.refresh_token = AsyncMock(return_value="new-access-token")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_auth)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_refresh_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["accessToken"] == "new-access-token"
        assert data["refreshToken"] is None

        app.dependency_overrides.clear()
