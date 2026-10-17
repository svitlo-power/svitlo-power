"""Tests for app lifespan."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.lifespan import lifespan


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self):
        """Test lifespan startup and shutdown."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_app.state.injector.get.return_value = mock_beanie_initializer
        
        # Use the lifespan context manager
        async with lifespan(mock_app):
            # Startup should have been called
            mock_beanie_initializer.init.assert_called_once()
        
        # After exiting context, shutdown should be logged (but we can't easily test logging)
        # The yield happens, then the code after yield runs

    @pytest.mark.asyncio
    async def test_lifespan_with_exception(self):
        """Test lifespan handles exceptions during startup."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer.init.side_effect = Exception("Connection failed")
        mock_app.state.injector.get.return_value = mock_beanie_initializer
        
        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(mock_app):
                pass
        
        mock_beanie_initializer.init.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])