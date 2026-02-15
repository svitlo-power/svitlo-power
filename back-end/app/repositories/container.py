from injector import Binder, Module, noscope

from .interfaces import (
    IMessagesRepository,
    IStationsRepository,
    IStationsDataRepository,
    IUsersRepository,
    IVisitsCounterRepository,
    ILookupsRepository,
    IBotsRepository,
    IChatsRepository,
    IExtDataRepository,
    IExtDeviceRepository,
    IDashboardRepository,
)
from .implementations import (
    MessagesRepository,
    StationsRepository,
    StationsDataRepository,
    UsersRepository,
    VisitsCounterRepository,
    LookupsRepository,
    BotsRepository,
    ChatsRepository,
    ExtDataRepository,
    ExtDeviceRepository,
    DashboardRepository,
)


class RepositoryContainer(Module):

    def configure(self, binder: Binder):
        binder.bind(IMessagesRepository, to=MessagesRepository, scope=noscope)
        binder.bind(IStationsRepository, to=StationsRepository, scope=noscope)
        binder.bind(IStationsDataRepository, to=StationsDataRepository, scope=noscope)
        binder.bind(IUsersRepository, to=UsersRepository, scope=noscope)
        binder.bind(IVisitsCounterRepository, to=VisitsCounterRepository, scope=noscope)
        binder.bind(ILookupsRepository, to=LookupsRepository, scope=noscope)
        binder.bind(IBotsRepository, to=BotsRepository, scope=noscope)
        binder.bind(IChatsRepository, to=ChatsRepository, scope=noscope)
        binder.bind(IExtDataRepository, to=ExtDataRepository, scope=noscope)
        binder.bind(IExtDeviceRepository, to=ExtDeviceRepository, scope=noscope)
        binder.bind(IDashboardRepository, to=DashboardRepository, scope=noscope)
