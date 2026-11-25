"""Tests for the Phase 5 snapshot refresh trigger contract."""
from shared.services.dashboard_snapshot.triggers import (
    REFRESH_REASONS,
    SNAPSHOT_REFRESH_CHANNEL,
    build_refresh_notification,
)


class TestSnapshotRefreshChannel:
    def test_channel_is_versioned_and_separate_from_the_invalidation_channel(self):
        # Overloading `cache:dashboard:v1:invalidations` would make a rebuild
        # trigger look like a snapshot publication to every BFF.
        assert SNAPSHOT_REFRESH_CHANNEL == "processing:triggers:snapshot-refresh"
        assert SNAPSHOT_REFRESH_CHANNEL != "cache:dashboard:v1:invalidations"

    def test_reasons_match_the_processing_trigger_endpoint(self):
        assert REFRESH_REASONS == (
            "config-change",
            "buildings-change",
            "station-change",
            "outages-change",
        )


class TestBuildRefreshNotification:
    def test_payload_carries_reason_and_source(self):
        assert build_refresh_notification("buildings-change") == {
            "reason": "buildings-change",
            "source": "back-end",
        }

    def test_changed_sections_are_included_when_supplied(self):
        assert build_refresh_notification(
            "buildings-change", changed_sections=["buildings"]
        ) == {
            "reason": "buildings-change",
            "source": "back-end",
            "changedSections": ["buildings"],
        }

    def test_empty_changed_sections_are_omitted(self):
        assert "changedSections" not in build_refresh_notification(
            "config-change", changed_sections=[]
        )

    def test_source_can_be_overridden(self):
        assert build_refresh_notification("manual", source="back-end-2")["source"] == (
            "back-end-2"
        )