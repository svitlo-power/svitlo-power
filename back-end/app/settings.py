from functools import lru_cache
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.settings.base import BaseAppSettings, BaseDeyeAppSettings, BaseJWTSettings, BaseMongoSettings, BaseRedisSettings
from shared.utils import generate_secret_key


class Settings(BaseSettings, BaseAppSettings, BaseDeyeAppSettings, BaseJWTSettings, BaseMongoSettings, BaseRedisSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # -------------------------
    # Core
    # -------------------------

    SECRET_KEY: str = Field(default_factory=lambda: generate_secret_key(32))

    # -------------------------
    # Telegram
    # -------------------------
    TG_HOOK_BASE_URL: str | None = None

    BOT_TIMEZONE: str = "utc"

    # -------------------------
    # Push notifications (FCM)
    # -------------------------
    # Service account JSON or a path to the JSON file
    FIREBASE_CREDENTIALS: str | None = None

    # Defaults of the event trigger parameters; admins can change them in the push templates
    PUSH_OUTAGE_LEAD_MINUTES: int = 30
    PUSH_POWER_DEBOUNCE_SECONDS: int = 60
    PUSH_BATTERY_LOW_THRESHOLD: int = 20
    PUSH_BATTERY_HYSTERESIS: int = 10

    # -------------------------
    # Outages schedule (YASNO)
    # -------------------------
    OUTAGES_REGION: int = 25
    OUTAGES_DSO: int = 902

    # -------------------------
    # Auth / Admin
    # -------------------------
    ADMIN_USER: str | None = None
    ADMIN_PASSWORD: str | None = None

    # -------------------------
    # Other
    # -------------------------
    HOST: str = "127.0.0.1"
    STATISTIC_KEEP_DAYS: int = 3
    SSE_PING_INTERVAL: int = 45


class ProductionSettings(Settings):
    DEBUG: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_DURATION: int = 3600


class DebugSettings(Settings):
    DEBUG: bool = True
    HOST: str = Field(default_factory=lambda: os.getenv("DEBUG_HOST", "127.0.0.1"))


CONFIG_MAP = {
    "Production": ProductionSettings,
    "Debug": DebugSettings,
}


@lru_cache
def get_settings():
    debug = os.getenv("DEBUG", "False") == "True"
    mode = "Debug" if debug else "Production"
    return CONFIG_MAP[mode]()
