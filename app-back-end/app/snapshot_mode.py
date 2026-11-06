from fastapi import Request

from app.settings import Settings
from shared.features import FeatureFlag, feature_flags
from shared.models.dashboard_snapshot import DashboardSnapshot
from shared.services.dashboard_snapshot import DashboardSnapshotClient


def dashboard_snapshot_reads_enabled(settings: Settings) -> bool:
    return (
        settings.APP_BACKEND_REDIS_DASHBOARD_ENABLED
        and feature_flags.is_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH)
        and not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING)
    )


def active_dashboard_snapshot(
    request: Request,
    snapshot_client: DashboardSnapshotClient,
) -> DashboardSnapshot | None:
    if not dashboard_snapshot_reads_enabled(request.app.state.settings):
        return None

    snapshot = snapshot_client.get_snapshot()
    if snapshot is None or snapshot_client.is_stale:
        return None
    return snapshot
