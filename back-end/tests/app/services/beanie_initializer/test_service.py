"""Tests for app/services/beanie_initializer/service.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.beanie_initializer.service import BeanieInitializer


class TestBeanieInitializer:
    def test_init_stores_config(self):
        initializer = BeanieInitializer("mongodb://localhost:27017", "test-db")
        assert initializer._mongo_uri == "mongodb://localhost:27017"
        assert initializer._db_name == "test-db"
        assert initializer._client is None

    @pytest.mark.asyncio
    async def test_init_creates_client_and_initializes_beanie(self):
        initializer = BeanieInitializer("mongodb://localhost:27017", "test-db")

        with patch("app.services.beanie_initializer.service.AsyncMongoClient") as mock_client_cls, \
             patch("app.services.beanie_initializer.service.init_beanie") as mock_init_beanie:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            await initializer.init()

            mock_client_cls.assert_called_once_with("mongodb://localhost:27017")
            mock_init_beanie.assert_called_once()
            assert initializer._client is mock_client

    @pytest.mark.asyncio
    async def test_init_passes_correct_database(self):
        initializer = BeanieInitializer("mongodb://localhost:27017", "mydb")

        with patch("app.services.beanie_initializer.service.AsyncMongoClient") as mock_client_cls, \
             patch("app.services.beanie_initializer.service.init_beanie") as mock_init_beanie:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            await initializer.init()

            call_kwargs = mock_init_beanie.call_args
            assert call_kwargs[1]["database"] == mock_client["mydb"]
