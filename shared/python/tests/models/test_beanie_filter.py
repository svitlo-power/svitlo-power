"""Tests for shared/models/beanie_filter.py."""
from typing import get_args, Union

from shared.models.beanie_filter import MongoPrimitive, MongoValue, BeanieFilter


class TestMongoPrimitive:
    def test_str_is_primitive(self):
        assert str in get_args(MongoPrimitive)

    def test_int_is_primitive(self):
        assert int in get_args(MongoPrimitive)

    def test_float_is_primitive(self):
        assert float in get_args(MongoPrimitive)

    def test_bool_is_primitive(self):
        assert bool in get_args(MongoPrimitive)

    def test_none_is_primitive(self):
        assert type(None) in get_args(MongoPrimitive)


class TestMongoValue:
    def test_str_is_mongo_value(self):
        assert str in get_args(MongoValue)

    def test_list_of_primitives_is_mongo_value(self):
        from typing import List
        assert List[MongoPrimitive] in get_args(MongoValue)

    def test_dict_is_mongo_value(self):
        from typing import Dict, Any
        assert Dict[str, Any] in get_args(MongoValue)


class TestBeanieFilter:
    def test_beanie_filter_is_dict_alias(self):
        # BeanieFilter is a type alias for Dict[str, MongoValue]
        from typing import get_origin
        assert get_origin(BeanieFilter) is dict

    def test_beanie_filter_accepts_string_values(self):
        f: BeanieFilter = {"name": "test"}
        assert f["name"] == "test"

    def test_beanie_filter_accepts_int_values(self):
        f: BeanieFilter = {"count": 42}
        assert f["count"] == 42

    def test_beanie_filter_accepts_list_values(self):
        f: BeanieFilter = {"tags": ["a", "b"]}
        assert f["tags"] == ["a", "b"]

    def test_beanie_filter_accepts_nested_dict(self):
        f: BeanieFilter = {"meta": {"key": "value"}}
        assert f["meta"]["key"] == "value"
