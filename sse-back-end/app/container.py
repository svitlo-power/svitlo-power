"""Dependency injection container for sse-back-end."""
from injector import Injector, Module, provider, singleton
import redis.asyncio as redis
from shared.services import EventsService
from shared.services.events.models import EventsServiceConfig
from app.settings import Settings


class SSEModule(Module):
    @singleton
    @provider
    def provide_redis_client(self, settings: Settings) -> redis.Redis:
        return redis.Redis.from_url(str(settings.REDIS_URI), decode_responses=True)
    
    @singleton
    @provider
    def provide_events_service(self, settings: Settings) -> EventsService:
        config = EventsServiceConfig(str(settings.REDIS_URI), settings.DEBUG)
        return EventsService(config)


def create_injector(settings: Settings) -> Injector:
    return Injector([SSEModule()])


_injector: Injector | None = None


def set_injector(app, injector: Injector):
    global _injector
    _injector = injector
    app.state.injector = injector


def get_injector(app) -> Injector | None:
    return getattr(app.state, 'injector', _injector)