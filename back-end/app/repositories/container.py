from injector import Binder, Module, noscope, singleton

from .interfaces import (
    IMessagesRepository,
    IStationsRepository,
    IStationsDataRepository,
    IStationConnectionsRepository,
    IUsersRepository,
    IVisitsCounterRepository,
    ILookupsRepository,
    IBotsRepository,
    IChatsRepository,
    IExtDataRepository,
    IExtDeviceRepository,
    IDashboardRepository,
    ILoginHistoryRepository,
    IOutagesScheduleRepository,
    IPushDevicesRepository,
    IPushTopicsRepository,
)
from .implementations import (
    MessagesRepository,
    StationsRepository,
    StationsDataRepository,
    StationConnectionsRepository,
    UsersRepository,
    VisitsCounterRepository,
    LookupsRepository,
    BotsRepository,
    ChatsRepository,
    ExtDataRepository,
    ExtDeviceRepository,
    DashboardRepository,
    LoginHistoryRepository,
    PushDevicesRepository,
    PushTopicsRepository,
)
from shared.repositories.implementations import (
    RedisOutagesScheduleRepository,
    InMemoryOutagesScheduleRepository,
    DashboardReadRepository,
    ExtDataReadRepository,
    StationsReadRepository,
    StationsDataReadRepository,
    UsersReadRepository,
)
from shared.repositories.interfaces import (
    IDashboardReadRepository,
    IExtDataReadRepository,
    IStationsReadRepository,
    IStationsDataReadRepository,
    IUsersReadRepository,
)
from app.settings import Settings


class RepositoryContainer(Module):

    def __init__(self, settings: Settings):
        self._settings = settings

    def configure(self, binder: Binder):
        binder.bind(IMessagesRepository, to=MessagesRepository, scope=noscope)
        binder.bind(IStationsRepository, to=StationsRepository, scope=noscope)
        binder.bind(IStationsDataRepository, to=StationsDataRepository, scope=noscope)
        binder.bind(IStationConnectionsRepository, to=StationConnectionsRepository, scope=noscope)
        binder.bind(IUsersRepository, to=UsersRepository, scope=noscope)
        binder.bind(IVisitsCounterRepository, to=VisitsCounterRepository, scope=noscope)
        binder.bind(ILookupsRepository, to=LookupsRepository, scope=noscope)
        binder.bind(IBotsRepository, to=BotsRepository, scope=noscope)
        binder.bind(IChatsRepository, to=ChatsRepository, scope=noscope)
        binder.bind(IExtDataRepository, to=ExtDataRepository, scope=noscope)
        binder.bind(IExtDeviceRepository, to=ExtDeviceRepository, scope=noscope)
        binder.bind(IDashboardRepository, to=DashboardRepository, scope=noscope)
        binder.bind(IDashboardReadRepository, to=DashboardReadRepository, scope=noscope)
        binder.bind(IExtDataReadRepository, to=ExtDataReadRepository, scope=noscope)
        binder.bind(IStationsReadRepository, to=StationsReadRepository, scope=noscope)
        binder.bind(IStationsDataReadRepository, to=StationsDataReadRepository, scope=noscope)
        binder.bind(IUsersReadRepository, to=UsersReadRepository, scope=noscope)
        binder.bind(ILoginHistoryRepository, to=LoginHistoryRepository, scope=noscope)

        # Bind outages schedule repository based on DEBUG flag
        if self._settings.DEBUG:
            binder.bind(IOutagesScheduleRepository, to=InMemoryOutagesScheduleRepository, scope=singleton)
        else:
            redis_repo = RedisOutagesScheduleRepository(str(self._settings.REDIS_URI))
            binder.bind(IOutagesScheduleRepository, to=redis_repo, scope=singleton)
        binder.bind(IPushDevicesRepository, to=PushDevicesRepository, scope=noscope)
        binder.bind(IPushTopicsRepository, to=PushTopicsRepository, scope=noscope)
