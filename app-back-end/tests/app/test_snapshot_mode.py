import pytest

from app.settings import Settings
from app.snapshot_mode import dashboard_snapshot_reads_enabled
from shared.features import FeatureFlag, feature_flags


@pytest.mark.parametrize(
    ("reader_enabled", "publishing_enabled", "deye_processing", "expected"),
    [
        (False, True, False, False),
        (True, False, False, False),
        (True, True, True, False),
        (True, True, False, True),
    ],
)
def test_dashboard_snapshot_reads_require_compatible_modes(
    reader_enabled, publishing_enabled, deye_processing, expected
):
    flags = {
        FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH: feature_flags.is_enabled(
            FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH
        ),
        FeatureFlag.DEYE_POLLING_PROCESSING: feature_flags.is_enabled(
            FeatureFlag.DEYE_POLLING_PROCESSING
        ),
    }
    try:
        feature_flags.set_enabled(
            FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, publishing_enabled
        )
        feature_flags.set_enabled(
            FeatureFlag.DEYE_POLLING_PROCESSING, deye_processing
        )
        settings = Settings(
            APP_BACKEND_REDIS_DASHBOARD_ENABLED=reader_enabled
        )

        assert dashboard_snapshot_reads_enabled(settings) is expected
    finally:
        for flag, enabled in flags.items():
            feature_flags.set_enabled(flag, enabled)
