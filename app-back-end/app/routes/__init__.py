from app.routes.dashboard import register as register_dashboard
from app.routes.outages_schedule import register as register_outages_schedule


def register_routes(app):
    register_dashboard(app)
    register_outages_schedule(app)