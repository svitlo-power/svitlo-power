from app.settings import Settings
from shared.features import FeatureFlag, feature_flags


def dashboard_snapshot_reads_enabled(settings: Settings) -> bool:
    return (
        settings.APP_BACKEND_REDIS_DASHBOARD_ENABLED
        and feature_flags.is_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH)
        and not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING)
    )
