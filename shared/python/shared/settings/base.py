from datetime import timedelta
from typing import Annotated
from pydantic import BaseModel, Field, computed_field
from pydantic.networks import RedisDsn, UrlConstraints
from pydantic_core import MultiHostUrl

from shared.utils import generate_secret_key


type MongoDsn = Annotated[
    MultiHostUrl,
    UrlConstraints(allowed_schemes=["mongodb", "mongodb+srv"])
]


class BaseAppSettings(BaseModel):
    DEBUG: bool = Field(default=False)

    @computed_field
    @property
    def I18N_PATH(self) -> str:
        return "../shared/i18n"


class BaseDeyeAppSettings(BaseModel):
    DEYE_BASE_URL: str | None = None
    DEYE_APP_ID: str | None = None
    DEYE_APP_SECRET: str | None = None
    DEYE_EMAIL: str | None = None
    DEYE_PASSWORD: str | None = None

    DEYE_FETCH_INTERVAL: int = Field(default=120)
    DEYE_SYNC_STATIONS_ON_POLL: bool = Field(default=False)

    DEYE_REPORT_INTERVAL: int = Field(default=300)
    DEYE_ASSUMED_OFFLINE_REPORTS: int = Field(default=2)


class BaseJWTSettings(BaseModel):
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: generate_secret_key(64),
        description="JWT signing key (auto-generated if missing)."
    )

    JWT_ACCESS_TOKEN_EXPIRES_MIN: int = Field(
        default=60,
        description="Access token expiration in minutes."
    )

    JWT_REFRESH_TOKEN_EXPIRES_MIN: int = Field(
        default=60 * 24 * 7,
        description="Refresh token expiration in minutes."
    )

    @computed_field
    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRES_MIN)

    @computed_field
    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(minutes=self.JWT_REFRESH_TOKEN_EXPIRES_MIN)


class BaseRedisSettings(BaseModel):
    REDIS_URI: RedisDsn | None = Field(
        default=None,
        description="Redis DSN (redis:// or rediss://)."
    )

class BaseMongoSettings(BaseModel):
    MONGO_URI: MongoDsn = Field(
        default=None,
        description="Mongo URI (mongodb:// or mongodb+srv://)."
    )
    MONGO_DB: str = Field(
        default="svitlo-power",
        description="Mongo database name"
    )
