import aiohttp
from injector import Module, provider, singleton
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import redis.asyncio as redis

from app.settings import settings
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
    def provide_motor_client(self) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(settings.MONGODB_URI)

    @singleton
    @provider
    async def provide_beanie_init(self, client: AsyncIOMotorClient) -> None:
        await init_beanie(
            database=client[settings.MONGODB_DB],
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
    def provide_redis_client(self) -> redis.Redis:
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

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