from datetime import datetime, timedelta
from injector import Injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.settings import Settings
from app.services import StationConnectionsService, StationsService
from shared.features import feature_flags, FeatureFlag


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def sync_stations(connection_ids=None):
        stations: StationsService = injector.get(StationsService)
        await stations.sync_stations(connection_ids)

    async def sync_stations_data():
        stations: StationsService = injector.get(StationsService)
        await stations.sync_stations_data()

    async def check_deye_status():
        # Only run Deye polling if migration is enabled
        if not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING):
            connections: StationConnectionsService = injector.get(StationConnectionsService)
            sync_on_poll_ids = [
                c.id for c in connections.get_connections() if c.sync_stations_on_poll
            ]
            if sync_on_poll_ids:
                await sync_stations(sync_on_poll_ids)

                run_at = datetime.now() + timedelta(seconds=10)
                scheduler.add_job(
                    id       = "check_deye_continue",
                    func     = sync_stations_data,
                    trigger  = 'date',
                    run_date = run_at,
                )
                return

            await sync_stations_data()

    async def sync_stations_scheduled():
        # Only run scheduled sync if migration is enabled
        if not feature_flags.is_enabled(FeatureFlag.DEYE_POLLING_PROCESSING):
            connections: StationConnectionsService = injector.get(StationConnectionsService)
            connection_ids = [
                c.id for c in connections.get_connections() if not c.sync_stations_on_poll
            ]
            if connection_ids:
                await sync_stations(connection_ids)

    scheduler.add_job(
        id            = 'check_deye_status',
        func          = check_deye_status,
        trigger       = 'interval',
        next_run_time = datetime.now(),
        seconds       = int(settings.DEYE_FETCH_INTERVAL),
    )
    scheduler.add_job(
        id            = 'sync_deye_stations',
        func          = sync_stations_scheduled,
        trigger       = 'cron',
        hour          = '*/3',
        minute        = '0',
        second        = '0',
        next_run_time = datetime.now()
    )
