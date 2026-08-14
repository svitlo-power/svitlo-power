"""Tests for app/models/sorting_config.py."""
import pytest
from pydantic import ValidationError

from app.models.sorting_config import SortingConfig


class TestSortingConfig:
    def test_ascending_sort(self):
        config = SortingConfig(column="name", order="asc")
        assert config.column == "name"
        assert config.order == "asc"

    def test_descending_sort(self):
        config = SortingConfig(column="created_at", order="desc")
        assert config.column == "created_at"
        assert config.order == "desc"

    def test_invalid_order_raises_error(self):
        with pytest.raises(ValidationError):
            SortingConfig(column="name", order="invalid")

    def test_missing_column_raises_error(self):
        with pytest.raises(ValidationError):
            SortingConfig(order="asc")

    def test_missing_order_raises_error(self):
        with pytest.raises(ValidationError):
            SortingConfig(column="name")

    def test_from_attributes(self):
        class MockObj:
            column = "test_col"
            order = "asc"

        config = SortingConfig.model_validate(MockObj())
        assert config.column == "test_col"
        assert config.order == "asc"
