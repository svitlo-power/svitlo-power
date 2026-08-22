"""Tests for app/models/api/ext_data.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import (
    GridPowerState,
    GridPowerRequest,
    ExtDataCreateRequest,
    ExtDataItemResponse,
    ExtDataListRequest,
    ExtDataListResponse,
)
from app.models import PagingConfig, PagingInfo, SortingConfig, FilterConfig, ColumnDataType
from app.models.filter_config import PrimitiveFilter


class TestGridPowerState:
    def test_valid_state(self):
        state = GridPowerState(state=True)
        assert state.state is True

    def test_false_state(self):
        state = GridPowerState(state=False)
        assert state.state is False


class TestGridPowerRequest:
    def test_valid_request(self):
        req = GridPowerRequest(grid_power=GridPowerState(state=True))
        assert req.grid_power.state is True


class TestExtDataCreateRequest:
    def test_valid_request(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        req = ExtDataCreateRequest(user_id=oid, grid_state=True, received_at=now)
        assert req.user_id == oid
        assert req.grid_state is True
        assert req.received_at == now

    def test_without_received_at(self):
        oid = PydanticObjectId()
        req = ExtDataCreateRequest(user_id=oid, grid_state=False)
        assert req.received_at is None


class TestExtDataItemResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = ExtDataItemResponse(
            id=oid,
            userId=oid,
            gridState=True,
            receivedAt=now,
        )
        assert resp.id == oid
        assert resp.user_id == oid
        assert resp.grid_state is True
        assert resp.received_at == now


class TestExtDataListRequest:
    def test_valid_request(self):
        paging = PagingConfig(page=1, pageSize=10)
        sorting = SortingConfig(column="received_at", order="desc")
        req = ExtDataListRequest(paging=paging, sorting=sorting, filters=[])
        assert req.paging.page == 1
        assert req.sorting.column == "received_at"
        assert req.filters == []

    def test_with_filters(self):
        paging = PagingConfig(page=1, pageSize=10)
        sorting = SortingConfig(column="received_at", order="desc")
        filters = [PrimitiveFilter(column="grid_state", dataType=ColumnDataType.Boolean, value=True)]
        req = ExtDataListRequest(paging=paging, sorting=sorting, filters=filters)
        assert len(req.filters) == 1


class TestExtDataListResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        item = ExtDataItemResponse(id=oid, userId=oid, gridState=True, receivedAt=now)
        paging = PagingInfo(page=1, pageSize=10, total=1)
        resp = ExtDataListResponse(data=[item], paging=paging)
        assert len(resp.data) == 1
        assert resp.paging.total == 1
