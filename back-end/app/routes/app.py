from shared.features import feature_flags

from shared.utils import get_version


def register(app):
    @app.get("/api/app/version")
    async def get_app_version():
        return {"version": get_version()}

    @app.get("/api/app/features")
    async def get_app_features():
        """Return all feature flags and their enabled state."""
        return feature_flags.get_all_flags()