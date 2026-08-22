"""Tests for app/services/message_generator/template_method.py."""
from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import MagicMock

from app.services.message_generator.template_method import TemplateMethod, TemplateMethodMode
from app.services.message_generator.models import TemplateRequest


class TestTemplateMethod:
    def test_init_stores_request_class_and_kwargs(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        assert method.RequestCls is TestRequest
        assert method.fixed_kwargs == {"value": 42}

    def test_init_extracts_param_names(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0
            extra: str = "default"

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        assert "value" in method.param_names
        assert "extra" in method.param_names

    def test_bind_collect_mode_returns_request(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        context = MagicMock()
        context.add_request = MagicMock(return_value="request_result")

        wrapped = method.bind(context, TemplateMethodMode.Collect)
        result = wrapped()
        assert result == "request_result"
        context.add_request.assert_called_once()

    def test_bind_resolve_mode_returns_resolved_value(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        context = MagicMock()
        context.get_resolved_value = MagicMock(return_value=MagicMock(value=42))

        wrapped = method.bind(context, TemplateMethodMode.Resolve)
        result = wrapped()
        assert result.value == 42
        context.get_resolved_value.assert_called_once()

    def test_bind_with_positional_args(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0
            extra: str = "default"

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        context = MagicMock()
        context.add_request = MagicMock(return_value="request_result")

        wrapped = method.bind(context, TemplateMethodMode.Collect)
        result = wrapped("extra_value")
        assert result == "request_result"
        call_args = context.add_request.call_args
        created_request = call_args[0][0]
        assert created_request.extra == "extra_value"
        assert created_request.value == 42

    def test_bind_with_kwargs_override(self):
        @dataclass(frozen=True)
        class TestRequest(TemplateRequest):
            name: ClassVar[str] = "test"
            value: int = 0

            async def resolve(self, injector):
                return self.value

        method = TemplateMethod(TestRequest, value=42)
        context = MagicMock()
        context.add_request = MagicMock(return_value="request_result")

        wrapped = method.bind(context, TemplateMethodMode.Collect)
        result = wrapped(value=99)
        assert result == "request_result"
        call_args = context.add_request.call_args
        created_request = call_args[0][0]
        assert created_request.value == 99

    def test_init_handles_value_error_on_signature(self):
        """Test init handles ValueError when getting signature."""
        class BadRequest:
            def __init__(self):
                pass
        
        # This should not raise
        method = TemplateMethod(BadRequest, value=42)
        assert method.RequestCls is BadRequest

    def test_init_handles_type_error_on_signature(self):
        """Test init handles TypeError when getting signature."""
        class BadRequest:
            def __init__(self, *args, **kwargs):
                pass
        
        # This should not raise
        method = TemplateMethod(BadRequest, value=42)
        assert method.RequestCls is BadRequest

    def test_init_removes_self_param(self):
        """Test init removes 'self' from param_names."""
        class RequestWithSelf:
            def __init__(self, value: int, extra: str = "default"):
                pass
        
        method = TemplateMethod(RequestWithSelf, value=42)
        assert "self" not in method.param_names
        assert "value" in method.param_names
        assert "extra" in method.param_names

    def test_init_handles_value_error_on_signature(self):
        """Test init handles ValueError when getting signature."""
        class BadRequest:
            def __init__(self):
                pass
        
        # This should not raise
        method = TemplateMethod(BadRequest, value=42)
        assert method.RequestCls is BadRequest

    def test_init_handles_type_error_on_signature(self):
        """Test init handles TypeError when getting signature."""
        class BadRequest:
            def __init__(self, *args, **kwargs):
                pass
        
        # This should not raise
        method = TemplateMethod(BadRequest, value=42)
        assert method.RequestCls is BadRequest
