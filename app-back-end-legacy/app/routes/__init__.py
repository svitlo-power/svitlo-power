from app.routes.dashboard import register as register_dashboard
from app.routes.outages_schedule import register as register_outages_schedule
from app.routes.push import register as register_push
from app.routes.health import register as register_health


def register_routes(app):
    register_dashboard(app)
    register_outages_schedule(app)
    register_push(app)
    register_health(app)