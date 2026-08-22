"""Tests for app/repositories/implementations/station_connections.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.station_connections import StationConnectionsRepository
from shared.models.station_connection import StationConnection

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
StationConnection.name = MagicMock()
StationConnection.id = MagicMock()


class TestStationConnectionsRepository:
    """Tests for StationConnectionsRepository."""

    @pytest.mark.asyncio
    async def test_get_connections(self):
        """Test get_connections."""
        mock_connections = [MagicMock(spec=StationConnection)]
        with patch.object(StationConnection, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_connections)
            repo = StationConnectionsRepository()
            result = await repo.get_connections()
            assert result == mock_connections
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection(self):
        """Test get_connection."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_connection = MagicMock(spec=StationConnection)
        with patch.object(StationConnection, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_connection
            repo = StationConnectionsRepository()
            result = await repo.get_connection(conn_id)
            assert result == mock_connection
            mock_find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_connection(self):
        """Test add_connection."""
        mock_connection = MagicMock(spec=StationConnection)
        mock_connection.insert = AsyncMock()
        repo = StationConnectionsRepository()
        result = await repo.add_connection(mock_connection)
        assert result == mock_connection
        mock_connection.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_connection(self):
        """Test save_connection."""
        mock_connection = MagicMock(spec=StationConnection)
        mock_connection.save = AsyncMock()
        repo = StationConnectionsRepository()
        await repo.save_connection(mock_connection)
        mock_connection.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_connection_found(self):
        """Test delete_connection when exists."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_connection = MagicMock(spec=StationConnection)
        mock_connection.delete = AsyncMock()
        
        repo = StationConnectionsRepository()
        with patch.object(repo, 'get_connection', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_connection
            await repo.delete_connection(conn_id)
            mock_connection.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_connection_not_found(self):
        """Test delete_connection when not found."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        repo = StationConnectionsRepository()
        with patch.object(repo, 'get_connection', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.delete_connection(conn_id) # should not throw

    @pytest.mark.asyncio
    async def test_count(self):
        """Test count."""
        with patch.object(StationConnection, 'find') as mock_find:
            mock_find.return_value.count = AsyncMock(return_value=42)
            repo = StationConnectionsRepository()
            result = await repo.count()
            assert result == 42
            mock_find.assert_called_once()
