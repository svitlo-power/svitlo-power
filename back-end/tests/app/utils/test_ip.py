"""Tests for app/utils/ip.py."""
from unittest.mock import MagicMock

from fastapi import Request

from app.utils.ip import get_client_ip


class TestGetClientIp:
    def test_returns_x_forwarded_for_first_ip(self):
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        result = get_client_ip(request)
        assert result == "192.168.1.1"

    def test_returns_x_forwarded_for_single_ip(self):
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.5"}
        result = get_client_ip(request)
        assert result == "203.0.113.5"

    def test_strips_whitespace_from_forwarded_ip(self):
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "  192.168.1.1  , 10.0.0.1"}
        result = get_client_ip(request)
        assert result == "192.168.1.1"

    def test_falls_back_to_client_host(self):
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        result = get_client_ip(request)
        assert result == "10.0.0.1"

    def test_returns_empty_string_when_no_headers_and_no_client(self):
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None
        result = get_client_ip(request)
        assert result == ""

    def test_x_forwarded_for_takes_precedence_over_client(self):
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        result = get_client_ip(request)
        assert result == "192.168.1.1"

    def test_empty_x_forwarded_for_falls_back_to_client(self):
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": ""}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        result = get_client_ip(request)
        assert result == "10.0.0.1"
