"""Tests for grid-reporter health server."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.health_server import create_health_app, run_health_server
from shared.health import health_registry, HealthCheckResult, HealthStatus


class TestHealthServer:
    @pytest.mark.asyncio
    async def test_create_health_app(self):
        """Test that health app is created with correct routes."""
        with patch("app.main.register_health_checks"):
            app = await create_health_app()
            
            assert app is not None
            routes = [route.resource.canonical for route in app.router.routes()]
            assert "/health" in routes
            assert "/health/live" in routes
            assert "/health/ready" in routes
            assert "/metrics" in routes