"""Tests for app/models/api/api.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import (
    PageableRequest,
    SortableRequest,
    FilterableRequest,
    PageableResponse,
)
from app.models import PagingConfig, PagingInfo, SortingConfig, FilterConfig, ColumnDataType


class TestPageableRequest:
    def test_valid_request(self):
        paging = PagingConfig(page=1, pageSize=10)
        req = PageableRequest(paging=paging)
        assert req.paging.page == 1
        assert req.paging.page_size == 10

    def test_missing_paging_raises_error(self):
        with pytest.raises(ValidationError):
            PageableRequest()


class TestSortableRequest:
    def test_valid_request(self):
        sorting = SortingConfig(column="name", order="asc")
        req = SortableRequest(sorting=sorting)
        assert req.sorting.column == "name"
        assert req.sorting.order == "asc"

    def test_missing_sorting_raises_error(self):
        with pytest.raises(ValidationError):
            SortableRequest()


class TestFilterableRequest:
    def test_valid_request_with_filters(self):
        from app.models.filter_config import PrimitiveFilter
        filters = [PrimitiveFilter(column="name", dataType=ColumnDataType.Text, value="test")]
        req = FilterableRequest(filters=filters)
        assert len(req.filters) == 1

    def test_valid_request_without_filters(self):
        req = FilterableRequest(filters=[])
        assert req.filters == []

    def test_missing_filters_raises_error(self):
        with pytest.raises(ValidationError):
            FilterableRequest()


class TestPageableResponse:
    def test_valid_response(self):
        paging = PagingInfo(page=1, pageSize=10, total=100)
        resp = PageableResponse(data=[{"id": 1}], paging=paging)
        assert resp.data == [{"id": 1}]
        assert resp.paging.total == 100

    def test_generic_response_with_different_types(self):
        paging = PagingInfo(page=1, pageSize=10, total=5)
        resp = PageableResponse(data=["a", "b", "c"], paging=paging)
        assert len(resp.data) == 3
