from fastapi import Request

from shared.features import FeatureFlag, feature_flags
from shared.models.dashboard_snapshot import DashboardSnapshot
from shared.services.dashboard_snapshot import DashboardSnapshotClient


def dashboard_snapshot_reads_enabled() -> bool:
    # A snapshot producer exists once either the legacy back-end or Processing
    # publishes. Gating on the legacy flag alone would turn reads off at the
    # Phase 5 cutover, sending every client back to the per-request Mongo path.
    producer_publishing = feature_flags.is_enabled(
        FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH
    ) or feature_flags.is_enabled(
        FeatureFlag.PROCESSING_PUBLISH_ENABLED
    )
    return (
        feature_flags.is_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS)
        and producer_publishing
        and not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING)
    )


def active_dashboard_snapshot(
    request: Request,
    snapshot_client: DashboardSnapshotClient,
) -> DashboardSnapshot | None:
    if not dashboard_snapshot_reads_enabled():
        return None

    snapshot = snapshot_client.get_snapshot()
    if snapshot is None or snapshot_client.is_stale:
        return None
    return snapshot
