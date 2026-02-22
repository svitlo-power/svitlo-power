from datetime import timedelta
from pydantic import BaseModel, Field, MongoDsn, computed_field
from pydantic.networks import RedisDsn

from shared.utils import generate_secret_key


class BaseAppSettings(BaseModel):
    DEBUG: bool = Field(default=False)

    @computed_field
    @property
    def I18N_PATH(self) -> str:
        return "../shared/i18n"


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
        description="Mongo DSN (mongo://)."
    )
    MONGO_DB: str = Field(
        default="svitlo-power",
        description="Mongo database name"
    )
