"""Tests for shared/settings/base.py."""
from datetime import timedelta

import pytest
from pydantic import ValidationError

from shared.settings.base import (
    BaseAppSettings,
    BaseJWTSettings,
    BaseRedisSettings,
    BaseMongoSettings,
    MongoDsn,
)


class TestBaseAppSettings:
    def test_debug_defaults_false(self):
        settings = BaseAppSettings()
        assert settings.DEBUG is False

    def test_debug_can_be_true(self):
        settings = BaseAppSettings(DEBUG=True)
        assert settings.DEBUG is True

    def test_i18n_path_computed_field(self):
        settings = BaseAppSettings()
        assert settings.I18N_PATH == "../shared/i18n"


class TestBaseJWTSettings:
    def test_secret_key_auto_generated(self):
        settings = BaseJWTSettings()
        assert settings.JWT_SECRET_KEY is not None
        assert len(settings.JWT_SECRET_KEY) == 64

    def test_secret_key_custom(self):
        settings = BaseJWTSettings(JWT_SECRET_KEY="my_custom_key")
        assert settings.JWT_SECRET_KEY == "my_custom_key"

    def test_access_token_expires_default(self):
        settings = BaseJWTSettings()
        assert settings.JWT_ACCESS_TOKEN_EXPIRES_MIN == 60

    def test_refresh_token_expires_default(self):
        settings = BaseJWTSettings()
        assert settings.JWT_REFRESH_TOKEN_EXPIRES_MIN == 60 * 24 * 7

    def test_access_token_expires_computed(self):
        settings = BaseJWTSettings(JWT_ACCESS_TOKEN_EXPIRES_MIN=30)
        assert settings.JWT_ACCESS_TOKEN_EXPIRES == timedelta(minutes=30)

    def test_refresh_token_expires_computed(self):
        settings = BaseJWTSettings(JWT_REFRESH_TOKEN_EXPIRES_MIN=120)
        assert settings.JWT_REFRESH_TOKEN_EXPIRES == timedelta(minutes=120)


class TestBaseRedisSettings:
    def test_redis_uri_defaults_none(self):
        settings = BaseRedisSettings()
        assert settings.REDIS_URI is None

    def test_redis_uri_custom(self):
        settings = BaseRedisSettings(REDIS_URI="redis://localhost:6379")
        assert str(settings.REDIS_URI) == "redis://localhost:6379/0"


class TestBaseMongoSettings:
    def test_mongo_db_defaults(self):
        settings = BaseMongoSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.MONGO_DB == "svitlo-power"

    def test_mongo_uri_custom(self):
        settings = BaseMongoSettings(MONGO_URI="mongodb://localhost:27017")
        assert str(settings.MONGO_URI) == "mongodb://localhost:27017"


class TestMongoDsn:
    def test_valid_mongodb_scheme(self):
        dsn = MongoDsn("mongodb://localhost:27017")
        assert str(dsn) == "mongodb://localhost:27017"

    def test_valid_mongodb_srv_scheme(self):
        dsn = MongoDsn("mongodb+srv://localhost:27017")
        assert str(dsn) == "mongodb+srv://localhost:27017"

    def test_invalid_scheme_raises_error(self):
        # MongoDsn is a type alias, validation happens when used in a model
        with pytest.raises(ValidationError):
            BaseMongoSettings(MONGO_URI="redis://localhost:6379")
