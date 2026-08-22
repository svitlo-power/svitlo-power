"""Tests for app/middlewares/language.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from app.middlewares.language import LanguageMiddleware
from shared import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE


class TestLanguageMiddleware:
    @pytest.mark.asyncio
    async def test_sets_language_from_accept_language_header(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {"accept-language": "uk,en;q=0.9"}
        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            await middleware.dispatch(request, call_next)
            mock_lang.set.assert_called_once_with("uk")

    @pytest.mark.asyncio
    async def test_falls_back_to_default_for_unsupported_language(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {"accept-language": "fr,en;q=0.9"}
        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            await middleware.dispatch(request, call_next)
            mock_lang.set.assert_called_once_with(DEFAULT_LANGUAGE)

    @pytest.mark.asyncio
    async def test_falls_back_to_default_when_no_header(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {}
        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            await middleware.dispatch(request, call_next)
            mock_lang.set.assert_called_once_with(DEFAULT_LANGUAGE)

    @pytest.mark.asyncio
    async def test_extracts_primary_language_from_complex_header(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {"accept-language": "en-US,en;q=0.9,uk;q=0.8"}
        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            await middleware.dispatch(request, call_next)
            mock_lang.set.assert_called_once_with("en")

    @pytest.mark.asyncio
    async def test_resets_language_after_call_next(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {"accept-language": "uk"}
        call_next = AsyncMock(return_value=MagicMock())

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            await middleware.dispatch(request, call_next)
            mock_lang.reset.assert_called_once_with("token")

    @pytest.mark.asyncio
    async def test_resets_language_even_on_exception(self):
        middleware = LanguageMiddleware(app=MagicMock())
        request = MagicMock(spec=Request)
        request.headers = {"accept-language": "uk"}
        call_next = AsyncMock(side_effect=Exception("test error"))

        with patch("app.middlewares.language.current_language") as mock_lang:
            mock_lang.set.return_value = "token"
            mock_lang.reset = MagicMock()
            with pytest.raises(Exception, match="test error"):
                await middleware.dispatch(request, call_next)
            mock_lang.reset.assert_called_once_with("token")

    @pytest.mark.asyncio
    async def test_supported_languages(self):
        assert "en" in SUPPORTED_LANGUAGES
        assert "uk" in SUPPORTED_LANGUAGES
