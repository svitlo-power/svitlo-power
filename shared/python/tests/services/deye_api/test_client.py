"""Tests for shared/services/deye_api/client.py."""
import hashlib
from dataclasses import is_dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.services.deye_api.client import BaseDeyeClient, DeyeCredentials


class TestDeyeCredentials:
    def test_is_dataclass(self):
        assert is_dataclass(DeyeCredentials)

    def test_is_frozen(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        with pytest.raises(Exception):
            creds.base_url = "http://other.com"

    def test_fields(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        assert creds.base_url == "http://test.com"
        assert creds.app_id == "app1"
        assert creds.app_secret == "secret"
        assert creds.email == "test@test.com"
        assert creds.password == "pass"


class TestBaseDeyeClientInit:
    def test_init_with_session(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        mock_session = MagicMock()
        client = BaseDeyeClient(creds, session=mock_session)
        assert client._creds == creds
        assert client._session == mock_session
        assert client._owns_session is False
        assert client._token is None

    def test_init_without_session(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        assert client._creds == creds
        assert client._session is None
        assert client._owns_session is True
        assert client._token is None


class TestBaseDeyeClientInitMethod:
    @pytest.mark.asyncio
    async def test_init_creates_session_and_gets_token(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        with patch("shared.services.deye_api.client.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            with patch.object(client, "_get_token", new_callable=AsyncMock, return_value="token123"):
                await client.init()
                assert client._session == mock_session
                assert client._token == "token123"

    @pytest.mark.asyncio
    async def test_init_with_existing_session(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        mock_session = MagicMock()
        client = BaseDeyeClient(creds, session=mock_session)
        with patch.object(client, "_get_token", new_callable=AsyncMock, return_value="token123"):
            await client.init()
            assert client._session == mock_session
            assert client._token == "token123"


class TestBaseDeyeClientShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_closes_owned_session(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        client = BaseDeyeClient(creds, session=mock_session)
        client._owns_session = True
        await client.shutdown()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_does_not_close_unowned_session(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        client = BaseDeyeClient(creds, session=mock_session)
        client._owns_session = False
        await client.shutdown()
        mock_session.close.assert_not_called()


class TestBaseDeyeClientGetToken:
    @pytest.mark.asyncio
    async def test_get_token_success(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"accessToken": "token123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        client._session = mock_session

        token = await client._get_token()
        assert token == "token123"

    @pytest.mark.asyncio
    async def test_get_token_failure_returns_none(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP Error"))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        client._session = mock_session

        token = await client._get_token()
        assert token is None

    @pytest.mark.asyncio
    async def test_get_token_password_hashed(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"accessToken": "token123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client._get_token()

        call_args = mock_session.post.call_args
        sent_payload = call_args.kwargs.get("json", call_args.args[1] if len(call_args.args) > 1 else {})
        expected_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
        assert sent_payload["password"] == expected_hash


class TestBaseDeyeClientRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_token(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        with patch.object(client, "_get_token", new_callable=AsyncMock, return_value="new_token"):
            await client.refresh_token()
            assert client._token == "new_token"


class TestSetAuthorizationToken:
    def test_set_authorization_token(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        headers = {}
        client._set_authorization_token(headers, "my_token")
        assert headers["Authorization"] == "Bearer my_token"

    def test_set_authorization_token_empty(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        headers = {}
        client._set_authorization_token(headers, "")
        assert headers["Authorization"] == "Bearer "


class TestBaseDeyeClientRequest:
    @pytest.mark.asyncio
    async def test_request_success(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        client._token = "token123"
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"success": True, "data": "value"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_response)
        client._session = mock_session

        result = await client.request("POST", "/endpoint", {"key": "value"})
        assert result == {"success": True, "data": "value"}

    @pytest.mark.asyncio
    async def test_request_no_token_refreshes(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        client._token = None
        with patch.object(client, "refresh_token", new_callable=AsyncMock) as mock_refresh:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={"success": True})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_response)
            client._session = mock_session

            await client.request("POST", "/endpoint", {})
            mock_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_request_401_retries(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        client._token = "old_token"

        call_count = [0]

        def make_mock_response():
            mock_resp = MagicMock()
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=None)
            return mock_resp

        def mock_request(*args, **kwargs):
            call_count[0] += 1
            mock_resp = make_mock_response()
            if call_count[0] == 1:
                mock_resp.status = 401
            else:
                mock_resp.status = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value={"success": True})
            return mock_resp

        mock_session = MagicMock()
        mock_session.request = mock_request
        client._session = mock_session

        with patch.object(client, "refresh_token", new_callable=AsyncMock, return_value=None):
            result = await client.request("POST", "/endpoint", {})
            assert result == {"success": True}
            assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_request_exception_returns_none(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        client._token = "token123"
        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=Exception("Connection error"))
        client._session = mock_session

        result = await client.request("POST", "/endpoint", {})
        assert result is None


class TestBaseDeyeClientStationMethods:
    @pytest.mark.asyncio
    async def test_get_station_list(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        with patch.object(client, "request", new_callable=AsyncMock, return_value={"stations": []}) as mock_req:
            result = await client.get_station_list(page=1, size=30)
            mock_req.assert_awaited_once_with("POST", "/station/list", {"page": 1, "size": 30})
            assert result == {"stations": []}

    @pytest.mark.asyncio
    async def test_get_station_data(self):
        creds = DeyeCredentials(
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        client = BaseDeyeClient(creds)
        with patch.object(client, "request", new_callable=AsyncMock, return_value={"data": "value"}) as mock_req:
            result = await client.get_station_data(station_id=42)
            mock_req.assert_awaited_once_with("POST", "/station/latest", {"stationId": 42})
            assert result == {"data": "value"}
