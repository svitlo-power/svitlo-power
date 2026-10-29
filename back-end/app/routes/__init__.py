import os
from shared.utils.registration import load_and_register_modules
from app.routes.health import register_health_checks


def register_routes(app):
    base_path = os.path.dirname(__file__)
    package = 'app.routes'
    load_and_register_modules(base_path, package, 'register', app)
    
    # Register health checks after routes are loaded (injector available)
    from app.state import get_injector
    injector = get_injector(app)
    if injector:
        from app.settings import Settings
        settings = app.state.settings
        register_health_checks(settings, injector)
