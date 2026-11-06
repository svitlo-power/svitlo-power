from fastapi import FastAPI

from shared.features import FeatureFlag, feature_flags
from shared.utils import get_version


def register(app: FastAPI):
    @app.get("/api/version", include_in_schema=False)
    @app.get("/api/app/version")
    async def get_backend_version():
        return get_version()

    @app.get("/api/app/features")
    async def get_backend_features() -> dict[str, bool]:
        return {
            "dashboardUpdatedEventEnabled": (
                feature_flags.is_enabled(FeatureFlag.DASHBOARD_UPDATED_EVENT)
                and feature_flags.is_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH)
                and not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING)
            ),
        }
