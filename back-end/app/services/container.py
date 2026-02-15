from injector import Binder, Module, singleton, noscope
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.settings import Settings
from shared.services import EventsService, EventsServiceConfig, TranslationService
from .beanie_initializer import BeanieInitializer
from .authorization import AuthorizationService
from .bots import BotConfig, BotsService
from .outages_schedule import OutagesScheduleService
from .telegram import TelegramConfig, TelegramService
from .deye_api import DeyeConfig, DeyeApiService
from .visit_counter import VisitCounterService
from .users import UsersService
from .stations import StationsService
from .messages import MessagesService
from .lookups import LookupsService
from .ext_data import ExtDataService
from .ext_device import ExtDeviceService
from .dashboard import DashboardService
from .maintenance import MaintenanceService
from .message_generator import MessageGeneratorService, MessageGeneratorConfig
from .message_processor import MessageProcessorService
from .interfaces import IMessageGeneratorService, IExtDeviceService


class ServicesContainer(Module):
    def __init__(self, settings: Settings):
        self._settings = settings

    def configure(self, binder: Binder):
        beanie = BeanieInitializer(
            mongo_uri=str(self._settings.MONGO_URI),
            db_name=self._settings.MONGO_DB,
        )
        binder.bind(BeanieInitializer, to=beanie, scope=singleton)

        binder.bind(AuthorizationService, scope=singleton)

        binder.bind(DeyeConfig, scope=noscope)
        binder.bind(DeyeApiService, scope=singleton)

        binder.bind(StationsService, scope=noscope)

        events_service_config = EventsServiceConfig(str(self._settings.REDIS_URI), self._settings.DEBUG)
        binder.bind(EventsServiceConfig, to=events_service_config, scope=noscope)
        binder.bind(EventsService, to=EventsService(events_service_config), scope=singleton)
        binder.bind(OutagesScheduleService, scope=singleton)

        binder.bind(TelegramConfig, scope=noscope)
        binder.bind(TelegramService, scope=singleton)

        binder.bind(BotConfig, scope=noscope)
        binder.bind(BotsService, scope=singleton)

        binder.bind(MessageGeneratorConfig, scope=noscope)
        binder.bind(IMessageGeneratorService, to=MessageGeneratorService, scope=noscope)

        binder.bind(MessageProcessorService, scope=noscope)

        binder.bind(VisitCounterService, scope=noscope)

        binder.bind(UsersService, scope=noscope)
        binder.bind(MessagesService, scope=noscope)
        binder.bind(LookupsService, scope=noscope)

        binder.bind(ExtDataService, scope=noscope)
        binder.bind(IExtDeviceService, to=ExtDeviceService)

        binder.bind(DashboardService, scope=noscope)

        scheduler = AsyncIOScheduler()
        binder.bind(AsyncIOScheduler, to=scheduler, scope=singleton)

        binder.bind(MaintenanceService, scope=noscope)

        translations_service = TranslationService(path=self._settings.I18N_PATH)
        binder.bind(TranslationService, to=translations_service, scope=singleton)
