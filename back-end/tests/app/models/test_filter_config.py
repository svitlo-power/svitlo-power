"""Tests for app/models/filter_config.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.filter_config import (
    BaseFilter,
    DateTimeFilter,
    PrimitiveFilter,
    ObjectIdFilter,
    FilterConfig,
)
from app.models.column_data_type import ColumnDataType
from app.models.date_value import DateValue
from app.models.date_range_value import DateRangeValue


class TestBaseFilter:
    def test_base_filter_with_alias(self):
        f = BaseFilter(column="test_col", dataType=ColumnDataType.Text)
        assert f.column == "test_col"
        assert f.data_type == ColumnDataType.Text

    def test_base_filter_from_attributes(self):
        class MockObj:
            column = "test_col"
            data_type = ColumnDataType.Number

        f = BaseFilter.model_validate(MockObj())
        assert f.column == "test_col"
        assert f.data_type == ColumnDataType.Number


class TestDateTimeFilter:
    def test_with_date_value(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        dv = DateValue(value=dt)
        f = DateTimeFilter(column="date_col", dataType=ColumnDataType.DateTime, value=dv)
        assert f.value == dv

    def test_with_date_range_value(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        drv = DateRangeValue(start=start, end=end)
        f = DateTimeFilter(column="date_col", dataType=ColumnDataType.DateTime, value=drv)
        assert f.value == drv

    def test_from_string_single_date(self):
        f = DateTimeFilter(column="date_col", dataType=ColumnDataType.DateTime, value="2024-01-01T12:00:00")
        assert isinstance(f.value, DateValue)

    def test_from_string_range_date(self):
        f = DateTimeFilter(
            column="date_col",
            dataType=ColumnDataType.DateTime,
            value="2024-01-01T12:00:00,2024-01-02T12:00:00",
        )
        assert isinstance(f.value, DateRangeValue)

    def test_invalid_value_raises_type_error(self):
        with pytest.raises((ValidationError, TypeError)):
            DateTimeFilter(column="date_col", dataType=ColumnDataType.DateTime, value=12345)


class TestPrimitiveFilter:
    def test_with_bool(self):
        f = PrimitiveFilter(column="active", dataType=ColumnDataType.Boolean, value=True)
        assert f.value is True

    def test_with_int(self):
        f = PrimitiveFilter(column="count", dataType=ColumnDataType.Number, value=42)
        assert f.value == 42

    def test_with_float(self):
        f = PrimitiveFilter(column="price", dataType=ColumnDataType.Number, value=19.99)
        assert f.value == 19.99

    def test_with_str(self):
        f = PrimitiveFilter(column="name", dataType=ColumnDataType.Text, value="test")
        assert f.value == "test"


class TestObjectIdFilter:
    def test_with_object_id(self):
        oid = PydanticObjectId()
        f = ObjectIdFilter(column="ref_id", dataType=ColumnDataType.Id, value=oid)
        assert f.value == oid

    def test_with_string_object_id(self):
        oid_str = "507f1f77bcf86cd799439011"
        f = ObjectIdFilter(column="ref_id", dataType=ColumnDataType.Id, value=oid_str)
        assert f.value == PydanticObjectId(oid_str)


class TestFilterConfigUnion:
    def test_datetime_filter_is_filter_config(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dv = DateValue(value=dt)
        f = DateTimeFilter(column="date_col", dataType=ColumnDataType.DateTime, value=dv)
        assert isinstance(f, FilterConfig)

    def test_primitive_filter_is_filter_config(self):
        f = PrimitiveFilter(column="name", dataType=ColumnDataType.Text, value="test")
        assert isinstance(f, FilterConfig)

    def test_object_id_filter_is_filter_config(self):
        oid = PydanticObjectId()
        f = ObjectIdFilter(column="ref_id", dataType=ColumnDataType.Id, value=oid)
        assert isinstance(f, FilterConfig)
