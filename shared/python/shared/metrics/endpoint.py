"""Prometheus metrics endpoint for FastAPI."""
from fastapi import FastAPI, Response
from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST


def add_metrics_endpoint(app: FastAPI, path: str = "/metrics"):
    """Add /metrics endpoint to FastAPI app."""
    
    @app.get(path, include_in_schema=False)
    async def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )