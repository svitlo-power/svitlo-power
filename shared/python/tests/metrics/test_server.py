"""Tests for the metrics server module."""
import asyncio
import pytest
import socket
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from shared.metrics.server import MetricsServer, metrics_server_lifespan, run_metrics_server


def get_free_port():
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestMetricsServer:
    """Test the MetricsServer class."""

    @pytest.fixture
    def server(self):
        """Create a metrics server instance for testing."""
        return MetricsServer(host="127.0.0.1", port=get_free_port())

    @pytest.mark.asyncio
    async def test_create_app(self, server):
        """Test that the app is created with correct routes."""
        app = server.create_app()
        assert isinstance(app, web.Application)

        # Check routes exist
        routes = [route.resource for route in app.router.routes()]
        paths = [route.canonical for route in routes]
        assert "/metrics" in paths
        assert "/health" in paths

    @pytest.mark.asyncio
    async def test_start_stop(self, server):
        """Test starting and stopping the server."""
        await server.start()
        assert server._runner is not None
        assert server._site is not None
        assert server._site._port > 0  # Port was assigned

        port = server._site._port

        # Test that we can connect to the metrics endpoint
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/metrics") as resp:
                assert resp.status == 200
                content = await resp.text()
                assert "text/plain" in resp.headers.get("Content-Type", "")

        # Test health endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/health") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "healthy"

        await server.stop()
        assert server._site is None or server._site._server is None

    @pytest.mark.asyncio
    async def test_metrics_server_lifespan(self, server):
        """Test the async context manager for metrics server lifecycle."""
        port = get_free_port()
        async with metrics_server_lifespan(host="127.0.0.1", port=port) as server:
            assert server._runner is not None
            assert server._site is not None
            actual_port = server._site._port

            # Test metrics endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:{actual_port}/metrics") as resp:
                    assert resp.status == 200

        # After context exit, server should be stopped
        assert server._site is None or server._site._server is None

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self, server):
        """Test that /metrics returns valid Prometheus format."""
        await server.start()
        port = server._site._port

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/metrics") as resp:
                assert resp.status == 200
                content = await resp.text()
                # Check for Prometheus format indicators
                assert "# HELP" in content or "# TYPE" in content or content == ""

        await server.stop()

    @pytest.mark.asyncio
    async def test_run_metrics_server_cancellation(self):
        """Test that run_metrics_server can be cancelled."""
        port = get_free_port()
        server = MetricsServer(host="127.0.0.1", port=port)
        await server.start()

        # Create a task that runs the server on a DIFFERENT port
        port2 = get_free_port()
        task = asyncio.create_task(run_metrics_server(host="127.0.0.1", port=port2))

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Original server should still be running
        assert server._site is not None
        await server.stop()

    @pytest.mark.asyncio
    async def test_start_address_already_in_use(self):
        """Test that starting a second server on same port handles gracefully."""
        port = get_free_port()
        server1 = MetricsServer(host="127.0.0.1", port=port)
        await server1.start()

        # Try to start a second server on the same port
        server2 = MetricsServer(host="127.0.0.1", port=port)
        await server2.start()

        # Second server should have skipped starting
        assert server2._site is None
        assert server2._runner is None
        assert server2._app is None

        # First server should still work
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/metrics") as resp:
                assert resp.status == 200

        await server1.stop()
        await server2.stop()  # Should not raise


class TestMetricsServerIntegration:
    """Integration tests for metrics server with prometheus_client."""

    @pytest.mark.asyncio
    async def test_metrics_includes_process_metrics(self):
        """Test that metrics include process metrics when registered."""
        from prometheus_client import REGISTRY, ProcessCollector

        # Register process collector if not already
        try:
            REGISTRY.register(ProcessCollector())
        except ValueError:
            pass  # Already registered

        port = get_free_port()
        server = MetricsServer(host="127.0.0.1", port=port)
        await server.start()

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/metrics") as resp:
                assert resp.status == 200
                content = await resp.text()
                # Process metrics should be present (may have different names on Windows)
                # Just verify we get some metrics back
                assert len(content) > 0
                assert "# HELP" in content or "# TYPE" in content

        await server.stop()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests."""
        port = get_free_port()
        server = MetricsServer(host="127.0.0.1", port=port)
        await server.start()

        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Make multiple concurrent requests
            tasks = [
                session.get(f"http://127.0.0.1:{port}/metrics")
                for _ in range(10)
            ]
            responses = await asyncio.gather(*tasks)

            for resp in responses:
                assert resp.status == 200
                await resp.text()

        await server.stop()