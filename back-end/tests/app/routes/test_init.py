"""Tests for app/routes/__init__.py."""
from unittest.mock import MagicMock, patch

import pytest

from app.routes import register_routes


class TestRegisterRoutes:
    def test_register_routes_calls_load_and_register_modules(self):
        """Test that register_routes calls load_and_register_modules with correct args."""
        mock_app = MagicMock()

        with patch("app.routes.load_and_register_modules") as mock_load:
            register_routes(mock_app)

            mock_load.assert_called_once()
            args, kwargs = mock_load.call_args
            assert args[1] == "app.routes"
            assert args[2] == "register"
            assert args[3] == mock_app

    def test_register_routes_passes_correct_base_path(self):
        """Test that register_routes passes the correct base_path."""
        mock_app = MagicMock()

        with patch("app.routes.load_and_register_modules") as mock_load:
            register_routes(mock_app)

            args, _ = mock_load.call_args
            import os
            expected_base_path = os.path.dirname(__file__).replace("tests\\app\\routes", "app\\routes")
            # The base_path should be the directory of app/routes/__init__.py
            assert "app" in args[0]
            assert "routes" in args[0]
