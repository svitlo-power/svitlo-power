"""Tests for app/services/ext_data/service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.ext_data.service import ExtDataService
from app.models.api import ExtDataItemResponse, ExtDataListRequest, ExtDataListResponse
from app.models import PagingConfig, SortingConfig
from shared.models.ext_data import ExtData
from shared.models.user import User


class TestExtDataServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        assert service._ext_data is mock_ext_data_repo
        assert service._users is mock_users_repo


class TestExtDataServiceProcessExtData:
    def test_process_ext_data_returns_response(self):
        mock_events = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)

        ext_data = ExtData(user_id=PydanticObjectId(), grid_state=True, received_at=datetime.now(timezone.utc))
        result = service._process_ext_data(ext_data)
        assert isinstance(result, ExtDataItemResponse)
        assert result.grid_state is True


class TestExtDataServiceAddExtData:
    @pytest.mark.asyncio
    async def test_add_ext_data_with_valid_user(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.add_ext_data = AsyncMock(return_value=PydanticObjectId())
        mock_users_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.add_ext_data("testuser", True)
        assert result is not None
        mock_users_repo.get_user.assert_called_once_with("testuser")
        mock_ext_data_repo.add_ext_data.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("ext_data_updated", None)

    @pytest.mark.asyncio
    async def test_add_ext_data_with_nonexistent_user(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.add_ext_data("nonexistent", True)
        assert result is None
        mock_ext_data_repo.add_ext_data.assert_not_called()


class TestExtDataServiceAddExtDataByUserId:
    @pytest.mark.asyncio
    async def test_add_ext_data_by_user_id_with_valid_user(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.add_ext_data = AsyncMock(return_value=PydanticObjectId())
        mock_users_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.add_ext_data_by_user_id(PydanticObjectId(), True)
        assert result is not None
        mock_users_repo.get_user_by_id.assert_called_once()
        mock_ext_data_repo.add_ext_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_ext_data_by_user_id_with_nonexistent_user(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.add_ext_data_by_user_id(PydanticObjectId(), True)
        assert result is None


class TestExtDataServiceGetExtData:
    @pytest.mark.asyncio
    async def test_get_ext_data_returns_response(self):
        mock_events = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        ext_data_list = [
            ExtData(user_id=PydanticObjectId(), grid_state=True, received_at=now),
            ExtData(user_id=PydanticObjectId(), grid_state=False, received_at=now),
        ]
        mock_ext_data_repo.get_ext_data = AsyncMock(return_value=(ext_data_list, 2))

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        request = ExtDataListRequest(
            paging=PagingConfig(page=1, pageSize=10),
            sorting=SortingConfig(column="received_at", order="desc"),
            filters=[],
        )
        result = await service.get_ext_data(request)
        assert isinstance(result, ExtDataListResponse)
        assert len(result.data) == 2
        assert result.paging.total == 2


class TestExtDataServiceGetById:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_response(self):
        mock_events = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        ext_data = ExtData(user_id=PydanticObjectId(), grid_state=True, received_at=now)
        mock_ext_data_repo.get_ext_data_by_id = AsyncMock(return_value=ext_data)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.get_by_id(PydanticObjectId())
        assert isinstance(result, ExtDataItemResponse)
        assert result.grid_state is True

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self):
        mock_events = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_ext_data_repo.get_ext_data_by_id = AsyncMock(return_value=None)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.get_by_id(PydanticObjectId())
        assert result is None


class TestExtDataServiceDeleteExtData:
    @pytest.mark.asyncio
    async def test_delete_ext_data_success(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_ext_data_repo.delete = AsyncMock(return_value=True)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.delete_ext_data(PydanticObjectId())
        assert result is True
        mock_events.broadcast_public.assert_called_once_with("ext_data_updated", None)

    @pytest.mark.asyncio
    async def test_delete_ext_data_not_found(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_ext_data_repo.delete = AsyncMock(return_value=False)

        service = ExtDataService(mock_events, mock_ext_data_repo, mock_users_repo)
        result = await service.delete_ext_data(PydanticObjectId())
        assert result is False
        mock_events.broadcast_public.assert_not_called()
