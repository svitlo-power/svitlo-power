from enum import Enum
from typing import Optional, List
from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from shared.models.localizable_value import LocalizableValue

# Re-export shared dashboard models
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    BuildingsSummaryRequest,
    ChargeSource,
    DashboardConfigResponse,
    EditBuildingResponse,
    PeriodResponse,
    PowerLogsRequest,
    PowerLogsResponse,
    SaveBuildingRequest,
    SaveDashboardConfigRequest,
)

__all__ = [
    "BuildingResponse",
    "BuildingSummaryResponse",
    "BuildingWithSummaryResponse",
    "BuildingsSummaryRequest",
    "ChargeSource",
    "DashboardConfigResponse",
    "EditBuildingResponse",
    "PeriodResponse",
    "PowerLogsRequest",
    "PowerLogsResponse",
    "SaveBuildingRequest",
    "SaveDashboardConfigRequest",
]