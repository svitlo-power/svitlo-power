import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.settings.base import BaseAppSettings, BaseJWTSettings, BaseMongoSettings, BaseRedisSettings
from shared.utils import generate_secret_key


class Settings(BaseSettings, BaseAppSettings, BaseJWTSettings, BaseMongoSettings, BaseRedisSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # YASNO API
    YASNO_REGION: int = 1
    YASNO_DSO: int = 1

    # JWT
    JWT_SECRET: str = Field(default_factory=lambda: generate_secret_key(64))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Override MongoDB to be optional for local development
    MONGO_URI: Optional[str] = Field(default="mongodb://localhost:27017", description="Mongo URI")
    MONGO_DB: str = "svitlo_power"

    # Override Redis to be optional for local development
    REDIS_URI: Optional[str] = Field(default="redis://localhost:6379/0", description="Redis URI")


class ProductionSettings(Settings):
    DEBUG: bool = False


class DebugSettings(Settings):
    DEBUG: bool = True
    HOST: str = Field(default_factory=lambda: os.getenv("DEBUG_HOST", "0.0.0.0"))


CONFIG_MAP = {
    "Production": ProductionSettings,
    "Debug": DebugSettings,
}


@lru_cache
def get_settings():
    debug = os.getenv("DEBUG", "False") == "True"
    mode = "Debug" if debug else "Production"
    return CONFIG_MAP[mode]()