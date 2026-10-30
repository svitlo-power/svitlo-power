"""Application state management."""
from fastapi import FastAPI
from injector import Injector


_injector: Injector | None = None


def set_injector(app: FastAPI, injector: Injector):
    """Set the injector for the application."""
    global _injector
    _injector = injector
    app.state.injector = injector


def get_injector(app: FastAPI) -> Injector | None:
    """Get the injector for the application."""
    return getattr(app.state, 'injector', _injector)