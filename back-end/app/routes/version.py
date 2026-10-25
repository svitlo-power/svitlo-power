from shared.utils import get_version


def register(app):
    @app.get("/api/version")
    async def get_backend_version():
        return get_version()
