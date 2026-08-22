"""Tests for shared/services/events/models.py."""
from dataclasses import is_dataclass

from shared.services.events.models import EventItem, EventsServiceConfig


class TestEventsServiceConfig:
    def test_is_not_dataclass(self):
        assert not is_dataclass(EventsServiceConfig)

    def test_init_sets_redis_uri(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        assert config.redis_uri == "redis://localhost:6379"

    def test_init_sets_is_debug(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=False)
        assert config.is_debug is False

    def test_str_representation(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        s = str(config)
        assert "redis://localhost:6379" in s
        assert "True" in s


class TestEventItem:
    def test_is_dataclass(self):
        assert is_dataclass(EventItem)

    def test_create_with_all_fields(self):
        item = EventItem(type="test", data={"key": "value"}, private=True, user="user1")
        assert item.type == "test"
        assert item.data == {"key": "value"}
        assert item.private is True
        assert item.user == "user1"

    def test_create_with_default_user(self):
        item = EventItem(type="test", data={}, private=False)
        assert item.user is None

    def test_to_dict(self):
        item = EventItem(type="test", data={"key": "value"}, private=True, user="user1")
        d = item.to_dict()
        assert d["type"] == "test"
        assert d["data"] == {"key": "value"}
        assert d["private"] is True
        assert d["user"] == "user1"

    def test_to_dict_with_none_user(self):
        item = EventItem(type="test", data={}, private=False)
        d = item.to_dict()
        assert d["user"] is None
