"""Tests for app/services/message_generator/context.py."""
from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.message_generator.context import (
    TemplateRequestCollector,
    TemplateRequestResolver,
    ResolvedValue,
    TemplateRequestContext,
)
from app.services.message_generator.models import TemplateRequest


class TestTemplateRequestCollector:
    def test_add_request_returns_request(self):
        collector = TemplateRequestCollector()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req = TestRequest(value=42)
        result = collector.add(req)
        assert result is req

    def test_requests_property_returns_set(self):
        collector = TemplateRequestCollector()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req1 = TestRequest(value=1)
        req2 = TestRequest(value=2)
        collector.add(req1)
        collector.add(req2)
        assert len(collector.requests) == 2

    def test_deduplicate_same_request(self):
        collector = TemplateRequestCollector()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req = TestRequest(value=1)
        collector.add(req)
        collector.add(req)
        assert len(collector.requests) == 1


class TestTemplateRequestResolver:
    @pytest.mark.asyncio
    async def test_resolve_requests_returns_dict(self):
        collector = TemplateRequestCollector()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req = TestRequest(value=42)
        collector.add(req)

        resolver = TemplateRequestResolver()
        injector = MagicMock()
        result = await resolver.resolve_requests(collector, injector)
        assert req in result
        assert result[req] == 42


class TestResolvedValue:
    def test_init_with_value(self):
        rv = ResolvedValue(42)
        assert rv.value == 42

    def test_init_with_none_value(self):
        rv = ResolvedValue(None)
        assert rv.value == 0

    def test_float_conversion(self):
        rv = ResolvedValue(42)
        assert float(rv) == 42.0

    def test_int_conversion(self):
        rv = ResolvedValue(42.7)
        assert int(rv) == 42

    def test_str_conversion(self):
        rv = ResolvedValue(42)
        assert str(rv) == "42"

    def test_repr_conversion(self):
        rv = ResolvedValue(42)
        assert repr(rv) == "42"

    def test_eq_comparison(self):
        rv = ResolvedValue(42)
        assert rv == 42

    def test_ne_comparison(self):
        rv = ResolvedValue(42)
        assert rv != 43

    def test_gt_comparison(self):
        rv = ResolvedValue(42)
        assert rv > 40

    def test_lt_comparison(self):
        rv = ResolvedValue(42)
        assert rv < 50

    def test_ge_comparison(self):
        rv = ResolvedValue(42)
        assert rv >= 42

    def test_le_comparison(self):
        rv = ResolvedValue(42)
        assert rv <= 42

    def test_add(self):
        rv = ResolvedValue(42)
        assert rv + 8 == 50

    def test_radd(self):
        rv = ResolvedValue(42)
        assert 8 + rv == 50

    def test_sub(self):
        rv = ResolvedValue(42)
        assert rv - 8 == 34

    def test_rsub(self):
        rv = ResolvedValue(42)
        assert 50 - rv == 8

    def test_mul(self):
        rv = ResolvedValue(42)
        assert rv * 2 == 84

    def test_rmul(self):
        rv = ResolvedValue(42)
        assert 2 * rv == 84

    def test_truediv(self):
        rv = ResolvedValue(42)
        assert rv / 2 == 21.0

    def test_rtruediv(self):
        rv = ResolvedValue(42)
        assert 84 / rv == 2.0

    def test_floordiv(self):
        rv = ResolvedValue(42)
        assert rv // 5 == 8

    def test_rfloordiv(self):
        rv = ResolvedValue(42)
        assert 100 // rv == 2

    def test_mod(self):
        rv = ResolvedValue(42)
        assert rv % 10 == 2

    def test_rmod(self):
        rv = ResolvedValue(42)
        assert 100 % rv == 100 % 42

    def test_pow(self):
        rv = ResolvedValue(2)
        assert rv ** 3 == 8

    def test_rpow(self):
        rv = ResolvedValue(3)
        assert 2 ** rv == 8


class TestTemplateRequestContext:
    def test_init_default(self):
        ctx = TemplateRequestContext()
        assert ctx._collect_data is False
        assert len(ctx._collected_data) == 0

    def test_init_with_collect_data(self):
        ctx = TemplateRequestContext(collect_data=True)
        assert ctx._collect_data is True

    def test_add_request(self):
        ctx = TemplateRequestContext()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req = TestRequest(value=42)
        result = ctx.add_request(req)
        assert result is req

    @pytest.mark.asyncio
    async def test_resolve_requests(self):
        ctx = TemplateRequestContext()

        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        req = TestRequest(value=42)
        ctx.add_request(req)

        injector = MagicMock()
        await ctx.resolve_requests(injector)
        assert ctx.get_resolved_value(req).value == 42

    def test_collected_data_property(self):
        ctx = TemplateRequestContext(collect_data=True)
        assert ctx.collected_data == []
