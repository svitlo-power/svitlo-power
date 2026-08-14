"""Tests for app/repositories/interfaces/base.py."""
from app.repositories.interfaces.base import DataQuery
from app.models import FilterConfig, SortingConfig, PagingConfig, ColumnDataType
from app.models.filter_config import PrimitiveFilter


class TestDataQuery:
    def test_init_with_all_params(self):
        filters = [PrimitiveFilter(column="name", dataType=ColumnDataType.Text, value="test")]
        sorting = SortingConfig(column="name", order="asc")
        paging = PagingConfig(page=1, pageSize=10)

        query = DataQuery(filters=filters, sorting=sorting, paging=paging)
        assert query.filters == filters
        assert query.sorting == sorting
        assert query.paging == paging

    def test_post_init_converts_none_filters_to_empty_dict(self):
        sorting = SortingConfig(column="name", order="asc")
        paging = PagingConfig(page=1, pageSize=10)

        query = DataQuery(filters=None, sorting=sorting, paging=paging)
        assert query.filters == {}

    def test_post_init_converts_empty_list_to_empty_dict(self):
        sorting = SortingConfig(column="name", order="asc")
        paging = PagingConfig(page=1, pageSize=10)

        query = DataQuery(filters=[], sorting=sorting, paging=paging)
        # __post_init__ converts falsy values (including []) to {}
        assert query.filters == {}
