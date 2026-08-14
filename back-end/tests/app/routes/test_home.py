"""Tests for app/routes/home.py."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.home import register
from app.utils.jwt_dependencies import jwt_required


class TestHomeRoute:
    def test_register_adds_route(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/" in routes

    def test_index_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 401

    def test_index_returns_message_with_valid_jwt(self):
        """Test that index returns the message when JWT is valid."""
        app = FastAPI()
        register(app)

        app.dependency_overrides[jwt_required] = lambda: {"user_id": "test"}
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == "Something weird happened if you see this..."
        app.dependency_overrides.clear()
