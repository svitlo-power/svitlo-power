"""Tests for app/utils/templating.py."""
import pytest

from app.utils.templating import (
    generate_message,
    get_send_timeout,
    get_should_send,
)


class TestGenerateMessage:
    @pytest.mark.asyncio
    async def test_simple_template(self):
        result = await generate_message("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_template_with_multiple_vars(self):
        result = await generate_message(
            "{{ greeting }}, {{ name }}!",
            {"greeting": "Hello", "name": "World"},
        )
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_template_with_macros(self):
        template_str = "{{ greeting(name) }}"
        template_macros = "{% macro greeting(name) %}Hello, {{ name }}!{% endmacro %}"
        result = await generate_message(template_str, {}, template_macros)
        assert result == "Hello, !"

    @pytest.mark.asyncio
    async def test_template_with_for_loop(self):
        template_str = "{% for item in items %}{{ item }}{% endfor %}"
        result = await generate_message(template_str, {"items": ["a", "b", "c"]})
        assert result == "abc"

    @pytest.mark.asyncio
    async def test_template_with_if_condition(self):
        template_str = "{% if show %}visible{% else %}hidden{% endif %}"
        result = await generate_message(template_str, {"show": True})
        assert result == "visible"

    @pytest.mark.asyncio
    async def test_template_with_if_condition_false(self):
        template_str = "{% if show %}visible{% else %}hidden{% endif %}"
        result = await generate_message(template_str, {"show": False})
        assert result == "hidden"

    @pytest.mark.asyncio
    async def test_template_error_raises_exception(self):
        with pytest.raises(Exception, match="Error in 'Message' template"):
            await generate_message("{{ undefined_var.attr }}", {})

    @pytest.mark.asyncio
    async def test_empty_template(self):
        result = await generate_message("", {})
        assert result == ""

    @pytest.mark.asyncio
    async def test_template_with_filters(self):
        result = await generate_message("{{ name | upper }}", {"name": "world"})
        assert result == "WORLD"


class TestGetSendTimeout:
    @pytest.mark.asyncio
    async def test_simple_timeout(self):
        result = await get_send_timeout("300", {})
        assert result == 300

    @pytest.mark.asyncio
    async def test_timeout_with_expression(self):
        result = await get_send_timeout("{{ 60 * 5 }}", {})
        assert result == 300

    @pytest.mark.asyncio
    async def test_timeout_with_variable(self):
        result = await get_send_timeout("{{ timeout }}", {"timeout": 120})
        assert result == 120

    @pytest.mark.asyncio
    async def test_timeout_error_raises_exception(self):
        with pytest.raises(Exception, match="Error in 'Send timeout' template"):
            await get_send_timeout("{{ undefined_var }}", {})


class TestGetShouldSend:
    @pytest.mark.asyncio
    async def test_none_template_returns_true(self):
        result = await get_should_send(None, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_true_string(self):
        result = await get_should_send("True", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_false_string(self):
        result = await get_should_send("False", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_true_with_variable(self):
        result = await get_should_send("{{ should_send }}", {"should_send": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_false_with_variable(self):
        result = await get_should_send("{{ should_send }}", {"should_send": False})
        assert result is False

    @pytest.mark.asyncio
    async def test_error_raises_exception(self):
        with pytest.raises(Exception, match="Error in 'Should send' template"):
            await get_should_send("{{ undefined_var.attr }}", {})
