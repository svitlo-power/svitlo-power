import aiohttp
from injector import Module, provider, singleton
from pymongo import AsyncMongoClient
from beanie import init_beanie
import redis.asyncio as redis

from app.settings import get_settings, Settings
from shared.repositories.implementations import (
    DashboardReadRepository,
    ExtDataReadRepository,
    StationsReadRepository,
    StationsDataReadRepository,
    UsersReadRepository,
    RedisOutagesScheduleRepository,
    InMemoryOutagesScheduleRepository,
    PushDevicesRepository,
    PushTopicsRepository,
)
from shared.repositories.interfaces import (
    IDashboardReadRepository,
    IExtDataReadRepository,
    IStationsReadRepository,
    IStationsDataReadRepository,
    IUsersReadRepository,
    IOutagesScheduleRepository,
    IPushDevicesRepository,
    IPushTopicsRepository,
)
from shared.services import (
    EventsService,
    ReadOnlyDashboardService,
    OutagesScheduleService,
    PushDevicesService,
    SettingsService,
)
from shared.services.events import EventsServiceConfig
from shared.models import (
    Building,
    DashboardConfig,
    ExtData,
    Station,
    StationData,
    User,
    OutagesSchedule,
    PushDevice,
    PushTopic,
)


class BeanieInitializer:
    def __init__(self, mongo_uri: str, db_name: str):
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: AsyncMongoClient | None = None

    async def init(self):
        self._client = AsyncMongoClient(self._mongo_uri)
        await init_beanie(
            database=self._client[self._db_name],
            document_models=[
                Building,
                DashboardConfig,
                ExtData,
                Station,
                StationData,
                User,
                OutagesSchedule,
                PushDevice,
                PushTopic,
            ],
        )


class AppModule(Module):
    @singleton
    @provider
    def provide_settings(self) -> Settings:
        return get_settings()

    @singleton
    @provider
    def provide_beanie_initializer(self, settings: Settings) -> BeanieInitializer:
        return BeanieInitializer(str(settings.MONGO_URI), settings.MONGO_DB)

    @singleton
    @provider
    def provide_redis_client(self, settings: Settings) -> redis.Redis:
        # Parse REDIS_URI to extract host, port, password, db
        redis_uri = str(settings.REDIS_URI) if settings.REDIS_URI else "redis://localhost:6379/0"
        # redis://[:password]@host:port/db
        return redis.Redis.from_url(redis_uri, decode_responses=True)

    @singleton
    @provider
    def provide_events_config(self, settings: Settings) -> EventsServiceConfig:
        redis_uri = str(settings.REDIS_URI) if settings.REDIS_URI else "redis://localhost:6379/0"
        return EventsServiceConfig(redis_uri, settings.DEBUG)

    @singleton
    @provider
    def provide_events_service(self, config: EventsServiceConfig) -> EventsService:
        return EventsService(config)

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
    def provide_stations_data_repository(self, settings: Settings) -> IStationsDataReadRepository:
        return StationsDataReadRepository(settings)

    @singleton
    @provider
    def provide_users_repository(self) -> IUsersReadRepository:
        return UsersReadRepository()

    @singleton
    @provider
    def provide_outages_schedule_repository(self, settings: Settings) -> IOutagesScheduleRepository:
        if settings.DEBUG:
            return InMemoryOutagesScheduleRepository()
        else:
            return RedisOutagesScheduleRepository(str(settings.REDIS_URI))

    @singleton
    @provider
    def provide_push_devices_repository(self) -> IPushDevicesRepository:
        return PushDevicesRepository()

    @singleton
    @provider
    def provide_push_topics_repository(self) -> IPushTopicsRepository:
        return PushTopicsRepository()

    @singleton
    @provider
    def provide_push_devices_service(
        self,
        devices: IPushDevicesRepository,
        topics: IPushTopicsRepository,
    ) -> PushDevicesService:
        return PushDevicesService(devices=devices, topics=topics)

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
        settings: SettingsService,
    ) -> ReadOnlyDashboardService:
        return ReadOnlyDashboardService(
            events=events,
            dashboard=dashboard,
            ext_data=ext_data,
            stations=stations,
            stations_data=stations_data,
            users=users,
            settings=settings,
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