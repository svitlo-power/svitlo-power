"""Tests for app/models/api/station_connections.py."""
import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import (
    CreateStationConnectionRequest,
    UpdateStationConnectionRequest,
    StationConnectionResponse,
    StationConnectionDefaultsResponse,
)


class TestUpdateStationConnectionRequest:
    def test_valid_request(self):
        req = UpdateStationConnectionRequest(
            name="Test Connection",
            baseUrl="https://api.example.com",
            appId="app123",
            appSecret="secret123",
            email="test@example.com",
            password="password123",
            syncStationsOnPoll=True,
        )
        assert req.name == "Test Connection"
        assert req.base_url == "https://api.example.com"
        assert req.app_id == "app123"
        assert req.app_secret == "secret123"
        assert req.email == "test@example.com"
        assert req.password == "password123"
        assert req.sync_stations_on_poll is True

    def test_optional_secrets(self):
        req = UpdateStationConnectionRequest(
            name="Test",
            baseUrl="https://api.example.com",
            appId="app123",
            email="test@example.com",
            syncStationsOnPoll=False,
        )
        assert req.app_secret is None
        assert req.password is None

    def test_empty_name_raises_error(self):
        with pytest.raises(ValidationError):
            UpdateStationConnectionRequest(
                name="",
                baseUrl="https://api.example.com",
                appId="app123",
                email="test@example.com",
                syncStationsOnPoll=False,
            )


class TestCreateStationConnectionRequest:
    def test_valid_request(self):
        req = CreateStationConnectionRequest(
            name="Test Connection",
            baseUrl="https://api.example.com",
            appId="app123",
            appSecret="secret123",
            email="test@example.com",
            password="password123",
            syncStationsOnPoll=True,
        )
        assert req.app_secret == "secret123"
        assert req.password == "password123"

    def test_missing_app_secret_raises_error(self):
        with pytest.raises(ValidationError):
            CreateStationConnectionRequest(
                name="Test",
                baseUrl="https://api.example.com",
                appId="app123",
                email="test@example.com",
                password="password123",
                syncStationsOnPoll=False,
            )

    def test_missing_password_raises_error(self):
        with pytest.raises(ValidationError):
            CreateStationConnectionRequest(
                name="Test",
                baseUrl="https://api.example.com",
                appId="app123",
                appSecret="secret123",
                email="test@example.com",
                syncStationsOnPoll=False,
            )


class TestStationConnectionResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        resp = StationConnectionResponse(
            id=oid,
            name="Test Connection",
            baseUrl="https://api.example.com",
            appId="app123",
            email="test@example.com",
            syncStationsOnPoll=True,
        )
        assert resp.id == oid
        assert resp.name == "Test Connection"
        assert resp.base_url == "https://api.example.com"
        assert resp.app_id == "app123"
        assert resp.email == "test@example.com"
        assert resp.sync_stations_on_poll is True


class TestStationConnectionDefaultsResponse:
    def test_valid_response(self):
        resp = StationConnectionDefaultsResponse(baseUrl="https://api.example.com")
        assert resp.base_url == "https://api.example.com"

    def test_none_base_url(self):
        resp = StationConnectionDefaultsResponse()
        assert resp.base_url is None
