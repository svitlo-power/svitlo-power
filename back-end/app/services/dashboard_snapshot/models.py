"""Pydantic models for DashboardSnapshot v1 schema.

Re-exports shared snapshot models from shared/models/snapshot.py.
Matches docs/architecture/snapshot-schema.json.
"""

from shared.models.snapshot import (
    BuildingSnapshot,
    ConfigSnapshot,
    DashboardSnapshot,
)

__all__ = [
    "BuildingSnapshot",
    "ConfigSnapshot",
    "DashboardSnapshot",
]
