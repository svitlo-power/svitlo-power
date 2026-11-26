"""Redis contract for the Phase 5 snapshot refresh trigger.

The legacy back-end used to call ``refresh_and_publish()`` inline from about a
dozen in-process sites. Once Processing owns publishing those calls cannot reach
it, so every mutation publishes a short "data changed" hint here instead.

The payload is a hint, never state: Processing re-reads MongoDB and rebuilds.
Delivery is fire and forget, so a Processing outage can never fail an admin
write, and bursts are coalesced on the receiving side.
"""

SNAPSHOT_REFRESH_CHANNEL = "processing:triggers:snapshot-refresh"

# Recognised reasons. Kept in sync with `SNAPSHOT_REFRESH_REASONS` in
# `shared/typescript/src/redis-keys.ts`, which validates the inbound trigger.
REFRESH_REASONS = (
    "config-change",
    "buildings-change",
    "station-change",
    "outages-change",
)


def build_refresh_notification(
    reason: str,
    source: str = "back-end",
    changed_sections: list[str] | None = None,
) -> dict:
    """Builds the pub/sub payload for one mutation.

    ``reason`` becomes a metric label on the Processing side, so an unknown
    value is rejected here rather than silently creating a new series (or being
    folded into ``other`` far from the call site).
    """
    if reason not in REFRESH_REASONS:
        raise ValueError(f"Unknown refresh reason: {reason!r}")
    notification: dict = {"reason": reason, "source": source}
    if changed_sections:
        notification["changedSections"] = changed_sections
    return notification