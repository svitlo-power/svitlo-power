"""Tests for app/repositories/implementations/base.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.models import FilterConfig, SortingConfig, PagingConfig, ColumnDataType
from app.repositories.implementations.base import (
    FilterableRepository,
    SortableRepository,
    PageableRepository,
    BaseReadRepository,
)


class TestFilterableRepository:
    """Tests for FilterableRepository.build_match_stage."""

    def test_build_match_stage_empty_filters(self):
        """Test build_match_stage with empty filters."""
        class MockModel:
            name = "test_field"

        repo = FilterableRepository()
        repo.model = MockModel
        result = repo.build_match_stage([])
        assert result == {}

    def test_build_match_stage_text_filter(self):
        """Test build_match_stage with text filter."""
        class MockModel:
            name = "test_field"

        repo = FilterableRepository()
        repo.model = MockModel
        
        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "name"
        filter_config.data_type = ColumnDataType.Text
        filter_config.value = "test"
        
        result = repo.build_match_stage([filter_config])
        assert result == {"test_field": {"$regex": "test", "$options": "i"}}

    def test_build_match_stage_number_filter(self):
        """Test build_match_stage with number filter."""
        class MockModel:
            age = "age_field"

        repo = FilterableRepository()
        repo.model = MockModel
        
        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "age"
        filter_config.data_type = ColumnDataType.Number
        filter_config.value = 25
        
        result = repo.build_match_stage([filter_config])
        assert result == {"age_field": 25}

    def test_build_match_stage_boolean_filter(self):
        """Test build_match_stage with boolean filter."""
        class MockModel:
            active = "active_field"

        repo = FilterableRepository()
        repo.model = MockModel
        
        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "active"
        filter_config.data_type = ColumnDataType.Boolean
        filter_config.value = True
        
        result = repo.build_match_stage([filter_config])
        assert result == {"active_field": True}

    def test_build_match_stage_id_filter(self):
        """Test build_match_stage with ID filter."""
        class MockModel:
            id = "id_field"

        repo = FilterableRepository()
        repo.model = MockModel
        
        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "id"
        filter_config.data_type = ColumnDataType.Id
        filter_config.value = "507f1f77bcf86cd799439011"
        
        result = repo.build_match_stage([filter_config])
        assert "id_field" in result
        assert isinstance(result["id_field"], PydanticObjectId)

    def test_build_match_stage_nonexistent_field(self):
        """Test build_match_stage with nonexistent field."""
        class MockModel:
            name = "name_field"

        repo = FilterableRepository()
        repo.model = MockModel
        
        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "nonexistent"
        filter_config.data_type = ColumnDataType.Text
        filter_config.value = "test"
        
        result = repo.build_match_stage([filter_config])
        assert result == {}


class TestSortableRepository:
    """Tests for SortableRepository.build_sort_stage."""

    def test_build_sort_stage_none_sorting(self):
        """Test build_sort_stage with None sorting."""
        repo = SortableRepository()
        result = repo.build_sort_stage(None)
        assert result == {}

    def test_build_sort_stage_ascending(self):
        """Test build_sort_stage with ascending order."""
        repo = SortableRepository()
        sorting = SortingConfig(column="name", order="asc")
        result = repo.build_sort_stage(sorting)
        assert result == {"name": 1}

    def test_build_sort_stage_descending(self):
        """Test build_sort_stage with descending order."""
        repo = SortableRepository()
        sorting = SortingConfig(column="created_at", order="desc")
        result = repo.build_sort_stage(sorting)
        assert result == {"created_at": -1}


class TestPageableRepository:
    """Tests for PageableRepository.get_paged_data."""

    @pytest.mark.asyncio
    async def test_get_paged_data_with_results(self):
        """Test get_paged_data with results."""
        class MockModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                        {"_id": "507f1f77bcf86cd799439012", "name": "test2"},
                    ],
                    "total": [{"count": 2}],
                }])
                return mock_cursor

        repo = PageableRepository()
        repo.model = MockModel
        
        data, total = await repo.get_paged_data([], 0, 10)
        assert len(data) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_paged_data_empty_results(self):
        """Test get_paged_data with empty results."""
        class MockModel:
            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [],
                    "total": [],
                }])
                return mock_cursor

        repo = PageableRepository()
        repo.model = MockModel
        
        data, total = await repo.get_paged_data([], 0, 10)
        assert data == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_paged_data_with_pagination(self):
        """Test get_paged_data with pagination."""
        class MockModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                    ],
                    "total": [{"count": 1}],
                }])
                return mock_cursor

        repo = PageableRepository()
        repo.model = MockModel
        
        data, total = await repo.get_paged_data([], 1, 5)
        assert len(data) == 1
        assert total == 1


class TestBaseReadRepository:
    """Tests for BaseReadRepository.get_data."""

    @pytest.mark.asyncio
    async def test_get_data_basic(self):
        """Test get_data with basic query."""
        class MockModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                    ],
                    "total": [{"count": 1}],
                }])
                return mock_cursor

        repo = BaseReadRepository()
        repo.model = MockModel

        query = MagicMock()
        query.filters = []
        query.sorting = None
        query.paging = None

        data, total = await repo.get_data(query)
        assert len(data) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_data_with_filters(self):
        """Test get_data with filters."""
        class MockModel:
            name = "name_field"

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
            
            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                    ],
                    "total": [{"count": 1}],
                }])
                return mock_cursor

        repo = BaseReadRepository()
        repo.model = MockModel

        filter_config = MagicMock(spec=FilterConfig)
        filter_config.column = "name"
        filter_config.data_type = ColumnDataType.Text
        filter_config.value = "test"

        query = MagicMock()
        query.filters = [filter_config]
        query.sorting = None
        query.paging = None

        data, total = await repo.get_data(query)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_get_data_with_sorting(self):
        """Test get_data with sorting."""
        class MockModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                    ],
                    "total": [{"count": 1}],
                }])
                return mock_cursor

        repo = BaseReadRepository()
        repo.model = MockModel

        sorting = SortingConfig(column="name", order="asc")

        query = MagicMock()
        query.filters = []
        query.sorting = sorting
        query.paging = None

        data, total = await repo.get_data(query)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_get_data_with_paging(self):
        """Test get_data with paging."""
        class MockModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def aggregate(cls, pipeline):
                mock_cursor = MagicMock()
                mock_cursor.to_list = AsyncMock(return_value=[{
                    "data": [
                        {"_id": "507f1f77bcf86cd799439011", "name": "test"},
                    ],
                    "total": [{"count": 1}],
                }])
                return mock_cursor

        repo = BaseReadRepository()
        repo.model = MockModel

        paging = PagingConfig(page=1, page_size=5)

        query = MagicMock()
        query.filters = []
        query.sorting = None
        query.paging = paging

        data, total = await repo.get_data(query)
        assert len(data) == 1

    def test_build_reference_joins_default(self):
        """Test build_reference_joins returns empty list by default."""
        repo = BaseReadRepository()
        result = repo.build_reference_joins(None)
        assert result == []