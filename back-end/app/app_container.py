from aiohttp import ClientSession
from fastapi import FastAPI
from fastapi_injector import attach_injector
from injector import Binder, Injector, Module, singleton

from app.settings import Settings
from .repositories import RepositoryContainer
from .services import ServicesContainer
from .services.authorization import AuthorizationService


class AppContainer(Module):
    def __init__(self, settings: Settings):
        self._settings = settings

    def configure(self, binder: Binder):
        binder.bind(Settings, to=self._settings, scope=singleton)
        binder.bind(AuthorizationService, scope=singleton)
        binder.bind(ClientSession, to=None)


def _create_containers(settings: Settings):
    app_container = AppContainer(settings)
    services_container = ServicesContainer(settings)
    repositories_container = RepositoryContainer(settings)
    return [app_container, services_container, repositories_container]

def init_container(app: FastAPI, settings: Settings) -> Injector:
    containers = _create_containers(settings)
    injector = Injector(containers)
    attach_injector(app, injector)
    return injector

def bind_client_session(injector: Injector):
    session = ClientSession()
    injector.binder.bind(ClientSession, to=session, scope=singleton)
