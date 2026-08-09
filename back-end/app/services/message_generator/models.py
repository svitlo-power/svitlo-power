from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from injector import Injector, inject

from app.settings import Settings


@inject
class MessageGeneratorConfig:
    timezone: str

    def __init__(self, settings: Settings):
        self.timezone = settings.BOT_TIMEZONE

    def __str__(self):
        return (f'MessageGeneratorConfig(timezone={self.timezone})')


@dataclass(frozen=True)
class TemplateRequest(ABC):
    @abstractmethod
    async def resolve(self, injector: Injector) -> Any:
        ...

    def describe(self) -> str:
        fields = ', '.join(f'{k}={v}' for k, v in self.__dict__.items())
        return f'{self.__class__.__name__}({fields})'


@dataclass(frozen=True)
class NumericTemplateRequest(TemplateRequest):

    def __float__(self):
        return 0.0

    def __int__(self):
        return 0

    def __str__(self):
        return "0"

    def __gt__(self, other):
        return False

    def __lt__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __le__(self, other):
        return False

    def __add__(self, other):
        return 0 + other

    def __radd__(self, other):
        return other + 0

    def __sub__(self, other):
        return 0 - other

    def __rsub__(self, other):
        return other - 0

    def __mul__(self, other):
        return 0 * other

    def __rmul__(self, other):
        return other * 0

    def __truediv__(self, other):
        return 0

    def __rtruediv__(self, other):
        return other
