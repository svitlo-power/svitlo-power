"""Internal routes for dashboard snapshot management."""

from fastapi import FastAPI, HTTPException
from fastapi_injector import Injected
from pydantic import BaseModel, Field

from app.services import DashboardSnapshotService


class SnapshotRefreshRequest(BaseModel):
    reason: str = "cache-miss"
    requested_by: str = Field("internal", alias="requestedBy")


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
        snapshot_service = Injected(DashboardSnapshotService),
    ) -> SnapshotRefreshResponse:
        """Trigger a dashboard snapshot refresh (internal endpoint).

        Internal BFF-to-backend endpoint called on cache misses.
        No user JWT required - authenticated via network segmentation.
        """
        result = await snapshot_service.handle_refresh_request(
            reason=body.reason,
            requested_by=body.requested_by,
        )
        return SnapshotRefreshResponse(**result)
