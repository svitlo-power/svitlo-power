"""Tests for app/services/message_generator/models.py."""
from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from injector import Injector

from app.services.message_generator.models import MessageGeneratorConfig, TemplateRequest, NumericTemplateRequest


class TestMessageGeneratorConfig:
    def test_init_with_settings(self):
        mock_settings = MagicMock()
        mock_settings.BOT_TIMEZONE = "Europe/Kiev"
        config = MessageGeneratorConfig(mock_settings)
        assert config.timezone == "Europe/Kiev"

    def test_str_representation(self):
        mock_settings = MagicMock()
        mock_settings.BOT_TIMEZONE = "utc"
        config = MessageGeneratorConfig(mock_settings)
        result = str(config)
        assert "timezone=utc" in result


class TestTemplateRequest:
    def test_describe_returns_name_and_fields(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test_request"
            field1: str = "value1"
            field2: int = 42

            async def resolve(self, injector):
                return self.field1

        req = TestRequest(field1="hello", field2=99)
        desc = req.describe()
        assert "test_request" in desc
        assert "field1=hello" in desc
        assert "field2=99" in desc


class TestNumericTemplateRequest:
    @pytest.fixture
    def concrete_request(self):
        class ConcreteNumericRequest(NumericTemplateRequest):
            name: ClassVar[str] = "numeric"

            async def resolve(self, injector):
                return 0

        return ConcreteNumericRequest

    def test_float_returns_zero(self, concrete_request):
        req = concrete_request()
        assert float(req) == 0.0

    def test_int_returns_zero(self, concrete_request):
        req = concrete_request()
        assert int(req) == 0

    def test_str_returns_zero(self, concrete_request):
        req = concrete_request()
        assert str(req) == "0"

    def test_gt_returns_false(self, concrete_request):
        req = concrete_request()
        assert (req > 10) is False

    def test_lt_returns_false(self, concrete_request):
        req = concrete_request()
        assert (req < 10) is False

    def test_ge_returns_false(self, concrete_request):
        req = concrete_request()
        assert (req >= 10) is False

    def test_le_returns_false(self, concrete_request):
        req = concrete_request()
        assert (req <= 10) is False

    def test_add_returns_other(self, concrete_request):
        req = concrete_request()
        assert (req + 10) == 10

    def test_radd_returns_other(self, concrete_request):
        req = concrete_request()
        assert (10 + req) == 10

    def test_sub_returns_negative(self, concrete_request):
        req = concrete_request()
        assert (req - 10) == -10

    def test_rsub_returns_other_minus_zero(self, concrete_request):
        req = concrete_request()
        assert (10 - req) == 10

    def test_mul_returns_zero(self, concrete_request):
        req = concrete_request()
        assert (req * 10) == 0

    def test_rmul_returns_zero(self, concrete_request):
        req = concrete_request()
        assert (10 * req) == 0

    def test_truediv_returns_zero(self, concrete_request):
        req = concrete_request()
        assert (req / 10) == 0

    def test_rtruediv_returns_other(self, concrete_request):
        req = concrete_request()
        assert (10 / req) == 10


# Need to import MagicMock for the config test
from unittest.mock import MagicMock
