"""Standalone metrics server for Prometheus metrics on a separate port."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from aiohttp import web
from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST


logger = logging.getLogger(__name__)


class MetricsServer:
    """Standalone aiohttp server for Prometheus metrics endpoint."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9090):
        self.host = host
        self.port = port
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._app: Optional[web.Application] = None

    def create_app(self) -> web.Application:
        """Create aiohttp app with metrics endpoint."""
        app = web.Application()

        async def metrics_handler(request):
            # CONTENT_TYPE_LATEST includes charset, but aiohttp doesn't allow it in content_type
            # So we use the content_type without charset and set charset separately
            content_type = CONTENT_TYPE_LATEST.split(';')[0]  # Remove charset
            return web.Response(
                body=generate_latest(REGISTRY),
                content_type=content_type,
                charset='utf-8'
            )

        async def health_handler(request):
            return web.json_response({"status": "healthy"})

        app.router.add_get("/metrics", metrics_handler)
        app.router.add_get("/health", health_handler)

        return app

    async def start(self):
        """Start the metrics server."""
        self._app = self.create_app()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host=self.host, port=self.port)
        try:
            await self._site.start()
            logger.info(f"Metrics server started on {self.host}:{self.port}")
        except OSError as e:
            # Handle "address already in use" on both Unix (errno 98) and Windows (errno 10048)
            if e.errno in (98, 10048):  # EADDRINUSE / WSAEADDRINUSE
                logger.warning(f"Metrics server port {self.port} already in use (likely another worker), skipping")
                self._site = None
                self._runner = None
                self._app = None
            else:
                raise

    async def stop(self):
        """Stop the metrics server."""
        if self._site:
            await self._site.stop()
            self._site = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        logger.info(f"Metrics server stopped on {self.host}:{self.port}")


@asynccontextmanager
async def metrics_server_lifespan(host: str = "0.0.0.0", port: int = 9090):
    """Async context manager for metrics server lifecycle."""
    server = MetricsServer(host=host, port=port)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


async def run_metrics_server(host: str = "0.0.0.0", port: int = 9090):
    """Run metrics server indefinitely (for standalone use)."""
    server = MetricsServer(host=host, port=port)
    await server.start()
    try:
        await asyncio.Event().wait()  # Run forever
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()