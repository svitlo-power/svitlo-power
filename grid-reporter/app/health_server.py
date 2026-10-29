"""Health check and metrics HTTP server for grid-reporter using aiohttp."""
import logging
from aiohttp import web
from prometheus_client import REGISTRY, generate_latest
from shared.health import health_registry


async def create_health_app() -> web.Application:
    """Create aiohttp app for health checks and metrics."""
    # Import here to avoid circular imports
    from app.main import register_health_checks
    register_health_checks()
    
    app = web.Application()
    
    async def health_handler(request):
        result = await health_registry.run_all()
        return web.json_response(result)
    
    async def liveness_handler(request):
        return web.json_response({"status": "alive"})
    
    async def readiness_handler(request):
        result = await health_registry.run_all()
        critical = ["deye_clients", "state_store"]
        ready = all(
            result["checks"].get(c, {}).get("status") == "healthy"
            for c in critical
        )
        return web.json_response({
            "status": "ready" if ready else "not_ready",
            "checks": {k: v for k, v in result["checks"].items() if k in critical}
        })
    
    async def metrics_handler(request):
        return web.Response(
            body=generate_latest(REGISTRY),
            content_type="text/plain; version=0.0.4"
        )
    
    app.router.add_get("/health", health_handler)
    app.router.add_get("/health/live", liveness_handler)
    app.router.add_get("/health/ready", readiness_handler)
    app.router.add_get("/metrics", metrics_handler)
    
    return app


async def run_health_server(port: int = 8081):
    """Run health check HTTP server using aiohttp."""
    health_app = await create_health_app()
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info(f"Health server started on port {port}")
    # Keep running
    await asyncio.Event().wait()