"""Tests for shared/models/lookup.py."""
import pytest

from shared.models.lookup import LookupValue, LookupModel
from shared.models.beanie_filter import BeanieFilter


class TestLookupValue:
    def test_create_lookup_value(self):
        from beanie import PydanticObjectId
        lv = LookupValue(value=PydanticObjectId(), text="Test")
        assert lv.text == "Test"

    def test_lookup_value_is_basemodel(self):
        from pydantic import BaseModel
        assert issubclass(LookupValue, BaseModel)

    def test_lookup_value_has_value_field(self):
        assert "value" in LookupValue.model_fields

    def test_lookup_value_has_text_field(self):
        assert "text" in LookupValue.model_fields


class TestLookupModel:
    def test_lookup_model_is_abstract(self):
        assert getattr(LookupModel, "__abstractmethods__", set())

    def test_lookup_model_has_get_lookup_values(self):
        assert hasattr(LookupModel, "get_lookup_values")

    def test_lookup_model_get_lookup_values_is_abstractmethod(self):
        assert "get_lookup_values" in LookupModel.__abstractmethods__
