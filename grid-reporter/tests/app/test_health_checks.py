"""Tests for grid-reporter health checks."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.health_checks import register_health_checks
from app.service import load_clients
from app.settings import load_settings
from app.state_store import StateStore
from shared.health import health_registry, HealthCheckResult, HealthStatus


class TestHealthChecks:
    def test_register_health_checks(self):
        """Test that health checks are registered."""
        # Clear registry first
        health_registry._checks.clear()
        
        register_health_checks()
        
        assert "deye_clients" in health_registry._checks
        assert "state_store" in health_registry._checks

    @pytest.mark.asyncio
    async def test_check_deye_clients_healthy(self):
        """Test deye_clients health check returns healthy when clients loaded."""
        from app.health_checks import register_health_checks
        register_health_checks()
        
        with patch("app.health_checks.load_settings") as mock_load_settings, \
             patch("app.health_checks.load_clients") as mock_load_clients:
            
            mock_settings = MagicMock()
            mock_load_settings.return_value = mock_settings
            mock_load_clients.return_value = [MagicMock(), MagicMock()]
            
            check_func = health_registry._checks["deye_clients"]
            result = await check_func()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.component == "deye_clients"
            assert result.details["clients_loaded"] == 2

    @pytest.mark.asyncio
    async def test_check_deye_clients_unhealthy(self):
        """Test deye_clients health check returns unhealthy on error."""
        from app.health_checks import register_health_checks
        register_health_checks()
        
        with patch("app.health_checks.load_settings") as mock_load_settings, \
             patch("app.health_checks.load_clients") as mock_load_clients:
            
            mock_load_settings.side_effect = Exception("Config error")
            
            check_func = health_registry._checks["deye_clients"]
            result = await check_func()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.component == "deye_clients"
            assert "Config error" in result.message

    @pytest.mark.asyncio
    async def test_check_state_store_healthy(self):
        """Test state_store health check returns healthy."""
        from app.health_checks import register_health_checks
        register_health_checks()
        
        with patch("app.health_checks.load_settings") as mock_load_settings, \
             patch("app.health_checks.StateStore") as mock_state_store_class:
            
            mock_settings = MagicMock()
            mock_settings.state_path = "/app/state.json"
            mock_load_settings.return_value = mock_settings
            
            mock_state_store = MagicMock()
            mock_state_store_class.return_value = mock_state_store
            
            check_func = health_registry._checks["state_store"]
            result = await check_func()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.component == "state_store"
            assert result.details["path"] == "/app/state.json"

    @pytest.mark.asyncio
    async def test_check_state_store_unhealthy(self):
        """Test state_store health check returns unhealthy on error."""
        from app.health_checks import register_health_checks
        register_health_checks()
        
        with patch("app.health_checks.load_settings") as mock_load_settings:
            mock_load_settings.side_effect = Exception("State error")
            
            check_func = health_registry._checks["state_store"]
            result = await check_func()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.component == "state_store"
            assert "State error" in result.message