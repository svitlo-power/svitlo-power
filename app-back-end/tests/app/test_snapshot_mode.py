import pytest
from types import SimpleNamespace

from app.settings import Settings
from app.snapshot_mode import (
    active_dashboard_snapshot,
    dashboard_snapshot_reads_enabled,
)
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


def test_active_snapshot_returns_fresh_snapshot(monkeypatch):
    monkeypatch.setattr("app.snapshot_mode.dashboard_snapshot_reads_enabled", lambda _: True)
    snapshot = object()
    snapshot_client = SimpleNamespace(
        get_snapshot=lambda: snapshot,
        is_stale=False,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=Settings()))
    )

    assert active_dashboard_snapshot(request, snapshot_client) is snapshot


def test_active_snapshot_rejects_stale_snapshot(monkeypatch):
    monkeypatch.setattr("app.snapshot_mode.dashboard_snapshot_reads_enabled", lambda _: True)
    snapshot_client = SimpleNamespace(get_snapshot=lambda: object(), is_stale=True)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=Settings()))
    )

    assert active_dashboard_snapshot(request, snapshot_client) is None


def test_active_snapshot_does_not_read_when_feature_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.snapshot_mode.dashboard_snapshot_reads_enabled", lambda _: False
    )
    snapshot_client = SimpleNamespace(
        get_snapshot=lambda: pytest.fail("snapshot should not be read"),
        is_stale=False,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=Settings()))
    )

    assert active_dashboard_snapshot(request, snapshot_client) is None
