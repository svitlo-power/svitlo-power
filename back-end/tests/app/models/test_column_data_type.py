"""Tests for app/models/column_data_type.py."""
from app.models.column_data_type import ColumnDataType


class TestColumnDataType:
    def test_text_value(self):
        assert ColumnDataType.Text == 1

    def test_number_value(self):
        assert ColumnDataType.Number == 2

    def test_datetime_value(self):
        assert ColumnDataType.DateTime == 4

    def test_boolean_value(self):
        assert ColumnDataType.Boolean == 8

    def test_id_value(self):
        assert ColumnDataType.Id == 16

    def test_is_int_enum(self):
        assert isinstance(ColumnDataType.Text, int)

    def test_all_values_unique(self):
        values = [e.value for e in ColumnDataType]
        assert len(values) == len(set(values))
