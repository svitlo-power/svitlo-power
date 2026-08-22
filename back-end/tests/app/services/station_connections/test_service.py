"""Tests for app/services/station_connections/service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.services.station_connections.service import StationConnectionsService
from app.services.deye_api.models import DeyeConfig
from app.services.deye_api.service import DeyeApiService
from app.utils.crypto import SecretCipher
from shared.models.station_connection import StationConnection


class TestStationConnectionsServiceInit:
    def test_init_stores_dependencies(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_settings.DEYE_BASE_URL = None
        mock_settings.DEYE_APP_ID = None
        mock_settings.DEYE_APP_SECRET = None
        mock_settings.DEYE_EMAIL = None
        mock_settings.DEYE_PASSWORD = None
        mock_settings.DEYE_SYNC_STATIONS_ON_POLL = False
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        assert service._settings is mock_settings
        assert service._connections_repo is mock_connections_repo
        assert service._stations_repo is mock_stations_repo
        assert service._session is mock_session
        assert service._connections == {}
        assert service._clients == {}


class TestStationConnectionsServiceGetConnections:
    def test_get_connections_returns_sorted_list(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn1 = StationConnection(name="Zebra", base_url="url1", app_id="id1", app_secret="secret", email="e1@test.com", password="pass")
        conn1.id = PydanticObjectId()
        conn2 = StationConnection(name="Alpha", base_url="url2", app_id="id2", app_secret="secret", email="e2@test.com", password="pass")
        conn2.id = PydanticObjectId()
        service._connections = {conn1.id: conn1, conn2.id: conn2}

        result = service.get_connections()
        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Zebra"


class TestStationConnectionsServiceGetConnection:
    def test_get_connection_returns_connection(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        service._connections = {conn.id: conn}

        result = service.get_connection(conn.id)
        assert result == conn

    def test_get_connection_returns_none_for_unknown_id(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        result = service.get_connection(PydanticObjectId())
        assert result is None


class TestStationConnectionsServiceCreateConnection:
    @pytest.mark.asyncio
    async def test_create_connection_encrypts_secrets(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        mock_connections_repo.add_connection = AsyncMock()

        result = await service.create_connection(
            name="Test",
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret123",
            email="test@example.com",
            password="password123",
            sync_stations_on_poll=True,
        )

        assert result.name == "Test"
        assert result.base_url == "https://api.example.com"
        # Verify secrets are encrypted
        assert result.app_secret != "secret123"
        assert result.password != "password123"
        mock_connections_repo.add_connection.assert_called_once()
        assert result.id in service._connections


class TestStationConnectionsServiceUpdateConnection:
    @pytest.mark.asyncio
    async def test_update_connection_success(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        service._connections = {conn.id: conn}

        mock_connections_repo.get_connection = AsyncMock(return_value=conn)
        mock_connections_repo.save_connection = AsyncMock()

        result = await service.update_connection(
            connection_id=conn.id,
            name="Updated",
            base_url="https://new.example.com",
            app_id="new_id",
            email="new@test.com",
            sync_stations_on_poll=False,
        )

        assert result.name == "Updated"
        assert result.base_url == "https://new.example.com"
        mock_connections_repo.save_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_connection_not_found_raises_value_error(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        mock_connections_repo.get_connection = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Cannot find Deye connection"):
            await service.update_connection(
                connection_id=PydanticObjectId(),
                name="Updated",
                base_url="https://new.example.com",
                app_id="new_id",
                email="new@test.com",
                sync_stations_on_poll=False,
            )


class TestStationConnectionsServiceDeleteConnection:
    @pytest.mark.asyncio
    async def test_delete_connection_removes_from_cache(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        service._connections = {conn.id: conn}

        mock_connections_repo.delete_connection = AsyncMock()

        await service.delete_connection(conn.id)
        assert conn.id not in service._connections
        mock_connections_repo.delete_connection.assert_called_once_with(conn.id)


class TestStationConnectionsServiceGetClient:
    @pytest.mark.asyncio
    async def test_get_client_returns_none_for_unknown_connection(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        result = await service.get_client(PydanticObjectId())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        cipher = SecretCipher(mock_settings.SECRET_KEY)
        conn = StationConnection(
            name="Test",
            base_url="https://api.example.com",
            app_id="app123",
            app_secret=cipher.encrypt("secret123"),
            email="test@example.com",
            password=cipher.encrypt("password123"),
        )
        service._connections = {conn.id: conn}

        with patch.object(DeyeApiService, "init", new_callable=AsyncMock):
            result = await service.get_client(conn.id)
            assert result is not None
            assert isinstance(result, DeyeApiService)
            assert conn.id in service._clients


class TestStationConnectionsServiceInit:
    @pytest.mark.asyncio
    async def test_init_migrate_and_load_connections(self):
        """Test init calls _migrate and loads connections."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_settings.DEYE_BASE_URL = None
        mock_settings.DEYE_APP_ID = None
        mock_settings.DEYE_APP_SECRET = None
        mock_settings.DEYE_EMAIL = None
        mock_settings.DEYE_PASSWORD = None
        mock_settings.DEYE_SYNC_STATIONS_ON_POLL = False
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        mock_connections_repo.get_connections = AsyncMock(return_value=[conn])
        mock_connections_repo.count = AsyncMock(return_value=1)
        mock_stations_repo.assign_connection_to_unassigned = AsyncMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        await service.init()
        assert service._connections == {conn.id: conn}

    @pytest.mark.asyncio
    async def test_init_migrate_creates_default_connection(self):
        """Test init creates default connection from env config."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_settings.DEYE_BASE_URL = "https://api.example.com"
        mock_settings.DEYE_APP_ID = "app123"
        mock_settings.DEYE_APP_SECRET = "secret123"
        mock_settings.DEYE_EMAIL = "test@example.com"
        mock_settings.DEYE_PASSWORD = "password123"
        mock_settings.DEYE_SYNC_STATIONS_ON_POLL = False
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        mock_connections_repo.count = AsyncMock(return_value=0)
        mock_connections_repo.add_connection = AsyncMock()
        mock_connections_repo.get_connections = AsyncMock(return_value=[])

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        await service.init()
        mock_connections_repo.add_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_migrate_no_env_config(self):
        """Test init does not create default connection when env config is missing."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_settings.DEYE_BASE_URL = None
        mock_settings.DEYE_APP_ID = None
        mock_settings.DEYE_APP_SECRET = None
        mock_settings.DEYE_EMAIL = None
        mock_settings.DEYE_PASSWORD = None
        mock_settings.DEYE_SYNC_STATIONS_ON_POLL = False
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        mock_connections_repo.count = AsyncMock(return_value=0)
        mock_connections_repo.get_connections = AsyncMock(return_value=[])

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        await service.init()
        mock_connections_repo.add_connection.assert_not_called()

    @pytest.mark.asyncio
    async def test_init_migrate_assigns_connection_to_stations(self):
        """Test init assigns connection to unassigned stations."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_settings.DEYE_BASE_URL = None
        mock_settings.DEYE_APP_ID = None
        mock_settings.DEYE_APP_SECRET = None
        mock_settings.DEYE_EMAIL = None
        mock_settings.DEYE_PASSWORD = None
        mock_settings.DEYE_SYNC_STATIONS_ON_POLL = False
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        mock_connections_repo.count = AsyncMock(return_value=1)
        mock_connections_repo.get_connections = AsyncMock(return_value=[conn])
        mock_stations_repo.assign_connection_to_unassigned = AsyncMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)
        await service.init()
        mock_stations_repo.assign_connection_to_unassigned.assert_called_once_with(conn.id)


class TestStationConnectionsServiceShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_calls_client_shutdown(self):
        """Test shutdown calls shutdown on all clients."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        mock_client1 = MagicMock()
        mock_client1.shutdown = AsyncMock()
        mock_client2 = MagicMock()
        mock_client2.shutdown = AsyncMock()

        service._clients = {"id1": mock_client1, "id2": mock_client2}

        await service.shutdown()
        mock_client1.shutdown.assert_called_once()
        mock_client2.shutdown.assert_called_once()
        assert service._clients == {}


class TestStationConnectionsServiceGetClientInvalidToken:
    @pytest.mark.asyncio
    async def test_get_client_invalid_token_returns_none(self):
        """Test get_client returns None when token is invalid."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn = StationConnection(
            name="Test",
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="invalid-encrypted-secret",
            email="test@example.com",
            password="invalid-encrypted-password",
        )
        service._connections = {conn.id: conn}

        result = await service.get_client(conn.id)
        assert result is None


class TestStationConnectionsServiceUpdateConnectionWithSecrets:
    @pytest.mark.asyncio
    async def test_update_connection_with_secrets(self):
        """Test update_connection encrypts new secrets."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        conn = StationConnection(name="Test", base_url="url", app_id="id", app_secret="secret", email="e@test.com", password="pass")
        service._connections = {conn.id: conn}

        mock_connections_repo.get_connection = AsyncMock(return_value=conn)
        mock_connections_repo.save_connection = AsyncMock()

        result = await service.update_connection(
            connection_id=conn.id,
            name="Updated",
            base_url="https://new.example.com",
            app_id="new_id",
            email="new@test.com",
            sync_stations_on_poll=False,
            app_secret="new_secret",
            password="new_password",
        )

        assert result.name == "Updated"
        assert result.app_secret != "new_secret"
        assert result.password != "new_password"
        mock_connections_repo.save_connection.assert_called_once()


class TestStationConnectionsServiceDropClient:
    @pytest.mark.asyncio
    async def test_drop_client_with_existing_client(self):
        """Test _drop_client shuts down existing client."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock()
        service._clients = {"conn_id": mock_client}

        await service._drop_client("conn_id")
        mock_client.shutdown.assert_called_once()
        assert "conn_id" not in service._clients

    @pytest.mark.asyncio
    async def test_drop_client_without_existing_client(self):
        """Test _drop_client does nothing when no client exists."""
        mock_settings = MagicMock()
        mock_settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
        mock_connections_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_session = MagicMock()

        service = StationConnectionsService(mock_settings, mock_connections_repo, mock_stations_repo, mock_session)

        await service._drop_client("nonexistent_id")
        assert "nonexistent_id" not in service._clients
