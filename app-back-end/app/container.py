import aiohttp
from injector import Module, provider, singleton
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import redis.asyncio as redis
from pydantic_core import MultiHostUrl

from app.settings import get_settings
from shared.repositories.implementations import (
    DashboardReadRepository,
    ExtDataReadRepository,
    StationsReadRepository,
    StationsDataReadRepository,
    UsersReadRepository,
    RedisOutagesScheduleRepository,
)
from shared.repositories.interfaces import (
    IDashboardReadRepository,
    IExtDataReadRepository,
    IStationsReadRepository,
    IStationsDataReadRepository,
    IUsersReadRepository,
    IOutagesScheduleRepository,
)
from shared.services import (
    EventsService,
    ReadOnlyDashboardService,
    OutagesScheduleService,
)
from shared.services.events.redis_transport import RedisTransport
from shared.models import (
    Building,
    DashboardConfig,
    ExtData,
    Station,
    StationData,
    User,
    OutagesSchedule,
)


class AppModule(Module):
    @singleton
    @provider
    def provide_settings(self) -> object:
        return get_settings()

    @singleton
    @provider
    def provide_motor_client(self, settings) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(str(settings.MONGO_URI))

    @singleton
    @provider
    async def provide_beanie_init(self, client: AsyncIOMotorClient, settings) -> None:
        await init_beanie(
            database=client[settings.MONGO_DB],
            document_models=[
                Building,
                DashboardConfig,
                ExtData,
                Station,
                StationData,
                User,
                OutagesSchedule,
            ],
        )

    @singleton
    @provider
    def provide_redis_client(self, settings) -> redis.Redis:
        # Parse REDIS_URI to extract host, port, password, db
        redis_uri = str(settings.REDIS_URI) if settings.REDIS_URI else "redis://localhost:6379/0"
        # redis://[:password]@host:port/db
        return redis.Redis.from_url(redis_uri, decode_responses=True)

    @singleton
    @provider
    def provide_redis_transport(self, redis_client: redis.Redis) -> RedisTransport:
        return RedisTransport(redis_client)

    @singleton
    @provider
    def provide_events_service(self, transport: RedisTransport) -> EventsService:
        return EventsService(transport)

    @singleton
    @provider
    def provide_aiohttp_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    @singleton
    @provider
    def provide_dashboard_repository(self) -> IDashboardReadRepository:
        return DashboardReadRepository()

    @singleton
    @provider
    def provide_ext_data_repository(self) -> IExtDataReadRepository:
        return ExtDataReadRepository()

    @singleton
    @provider
    def provide_stations_repository(self) -> IStationsReadRepository:
        return StationsReadRepository()

    @singleton
    @provider
    def provide_stations_data_repository(self) -> IStationsDataReadRepository:
        return StationsDataReadRepository()

    @singleton
    @provider
    def provide_users_repository(self) -> IUsersReadRepository:
        return UsersReadRepository()

    @singleton
    @provider
    def provide_outages_schedule_repository(self) -> IOutagesScheduleRepository:
            return RedisOutagesScheduleRepository()

    @singleton
    @provider
    def provide_dashboard_service(
        self,
        events: EventsService,
        dashboard: IDashboardReadRepository,
        ext_data: IExtDataReadRepository,
        stations: IStationsReadRepository,
        stations_data: IStationsDataReadRepository,
        users: IUsersReadRepository,
    ) -> ReadOnlyDashboardService:
        return ReadOnlyDashboardService(
            events=events,
            dashboard=dashboard,
            ext_data=ext_data,
            stations=stations,
            stations_data=stations_data,
            users=users,
        )

    @singleton
    @provider
    def provide_outages_schedule_service(
        self,
        events: EventsService,
        session: aiohttp.ClientSession,
        repository: IOutagesScheduleRepository,
    ) -> OutagesScheduleService:
        return OutagesScheduleService(
            events=events,
            session=session,
            repository=repository,
        )