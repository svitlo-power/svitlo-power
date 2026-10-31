"""Tests for grid-reporter health server."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

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

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test /health endpoint returns health check results."""
        with patch("app.main.register_health_checks"):
            app = await create_health_app()
            
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health")
                assert resp.status == 200
                data = await resp.json()
                assert "checks" in data

    @pytest.mark.asyncio
    async def test_liveness_endpoint(self):
        """Test /health/live endpoint returns alive status."""
        with patch("app.main.register_health_checks"):
            app = await create_health_app()
            
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health/live")
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self):
        """Test /health/ready endpoint returns readiness status."""
        with patch("app.main.register_health_checks"):
            app = await create_health_app()
            
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health/ready")
                assert resp.status == 200
                data = await resp.json()
                assert "status" in data
                assert data["status"] in ["ready", "not_ready"]

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test /metrics endpoint returns Prometheus metrics."""
        with patch("app.main.register_health_checks"):
            app = await create_health_app()
            
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/metrics")
                assert resp.status == 200
                content = await resp.text()
                assert "text/plain" in resp.headers.get("Content-Type", "")
                # Should contain Prometheus format
                assert "# HELP" in content or "# TYPE" in content or content == ""