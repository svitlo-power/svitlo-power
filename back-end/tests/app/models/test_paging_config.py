"""Tests for app/models/paging_config.py."""
import pytest
from pydantic import ValidationError

from app.models.paging_config import PagingConfig, PagingInfo


class TestPagingConfig:
    def test_minimal_config(self):
        config = PagingConfig(page=1, pageSize=10)
        assert config.page == 1
        assert config.page_size == 10

    def test_from_attributes(self):
        class MockObj:
            page = 2
            page_size = 20

        config = PagingConfig.model_validate(MockObj())
        assert config.page == 2
        assert config.page_size == 20

    def test_missing_page_raises_error(self):
        with pytest.raises(ValidationError):
            PagingConfig(page_size=10)

    def test_missing_page_size_raises_error(self):
        with pytest.raises(ValidationError):
            PagingConfig(page=1)


class TestPagingInfo:
    def test_paging_info_with_total(self):
        info = PagingInfo(page=1, pageSize=10, total=100)
        assert info.page == 1
        assert info.page_size == 10
        assert info.total == 100

    def test_paging_info_inherits_paging_config(self):
        info = PagingInfo(page=1, pageSize=10, total=50)
        assert isinstance(info, PagingConfig)
