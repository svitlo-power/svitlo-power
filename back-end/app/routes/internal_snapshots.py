"""Internal routes for dashboard snapshot management."""

from fastapi import FastAPI, Depends, HTTPException
from fastapi_injector import Injected
from pydantic import BaseModel

from app.services import DashboardSnapshotService
from app.utils.jwt_dependencies import jwt_required


class SnapshotRefreshRequest(BaseModel):
    reason: str = "cache-miss"
    requested_by: str = "internal"


class SnapshotRefreshResponse(BaseModel):
    accepted: bool
    epoch: int | None = None
    version: int | None = None
    coalesced: bool = False


def register(app: FastAPI):
    @app.post(
        "/internal/v1/snapshots/refresh",
        response_model=SnapshotRefreshResponse,
    )
    async def refresh_snapshot(
        body: SnapshotRefreshRequest,
        _ = Depends(jwt_required),
        snapshot_service = Injected(DashboardSnapshotService),
    ) -> SnapshotRefreshResponse:
        """Trigger a dashboard snapshot refresh (internal endpoint)."""
        result = await snapshot_service.handle_refresh_request(
            reason=body.reason,
            requested_by=body.requested_by,
        )
        return SnapshotRefreshResponse(**result)
