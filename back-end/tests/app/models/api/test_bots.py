"""Tests for app/models/api/bots.py."""
from beanie import PydanticObjectId
import pytest
from pydantic import ValidationError

from app.models.api import BotResponse, CreateBotRequest, UpdateBotRequest


class TestUpdateBotRequest:
    def test_valid_request(self):
        req = UpdateBotRequest(enabled=True, hookEnabled=False)
        assert req.enabled is True
        assert req.hook_enabled is False

    def test_missing_enabled_raises_error(self):
        with pytest.raises(ValidationError):
            UpdateBotRequest(hookEnabled=True)

    def test_missing_hook_enabled_raises_error(self):
        with pytest.raises(ValidationError):
            UpdateBotRequest(enabled=True)


class TestCreateBotRequest:
    def test_valid_request(self):
        req = CreateBotRequest(enabled=True, hookEnabled=True, token="test-token")
        assert req.enabled is True
        assert req.hook_enabled is True
        assert req.token == "test-token"

    def test_missing_token_raises_error(self):
        with pytest.raises(ValidationError):
            CreateBotRequest(enabled=True, hookEnabled=True)


class TestBotResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        resp = BotResponse(
            id=oid,
            name="Test Bot",
            token="test-token",
            enabled=True,
            hookEnabled=False,
        )
        assert resp.id == oid
        assert resp.name == "Test Bot"
        assert resp.token == "test-token"
        assert resp.enabled is True
        assert resp.hook_enabled is False
