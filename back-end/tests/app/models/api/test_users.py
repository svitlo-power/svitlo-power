"""Tests for app/models/api/users.py."""
import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import UserListResponseModel
from shared.models.user import ReportMode


class TestUserListResponseModel:
    def test_valid_response(self):
        oid = PydanticObjectId()
        resp = UserListResponseModel(
            id=oid,
            name="testuser",
            isActive=True,
            isReporter=False,
            apiKey="api-key-123",
            reportMode=ReportMode.EVENT,
        )
        assert resp.id == oid
        assert resp.name == "testuser"
        assert resp.is_active is True
        assert resp.is_reporter is False
        assert resp.api_key == "api-key-123"
        assert resp.report_mode == ReportMode.EVENT

    def test_defaults(self):
        oid = PydanticObjectId()
        resp = UserListResponseModel(id=oid, name="testuser")
        assert resp.is_active is True
        assert resp.is_reporter is False
        assert resp.api_key is None
        assert resp.report_mode is None

    def test_missing_id_raises_error(self):
        with pytest.raises(ValidationError):
            UserListResponseModel(name="testuser")

    def test_missing_name_raises_error(self):
        oid = PydanticObjectId()
        with pytest.raises(ValidationError):
            UserListResponseModel(id=oid)
