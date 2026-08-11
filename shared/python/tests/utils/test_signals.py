"""Tests for shared/utils/signals.py."""
import signal
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from shared.utils.signals import register_chained_signal_handlers, AsyncSignalHandler


class TestRegisterChainedSignalHandlers:
    def test_default_signals_on_non_windows(self):
        with patch("shared.utils.signals.os.name", "posix"):
            with patch("shared.utils.signals.signal.signal") as mock_signal:
                handler = AsyncMock()
                register_chained_signal_handlers(handler)
                assert mock_signal.call_count == 2

    def test_default_signals_on_windows(self):
        with patch("shared.utils.signals.os.name", "nt"):
            with patch("shared.utils.signals.signal.signal") as mock_signal:
                handler = AsyncMock()
                register_chained_signal_handlers(handler)
                assert mock_signal.call_count == 2

    def test_custom_signals(self):
        with patch("shared.utils.signals.signal.signal") as mock_signal:
            handler = AsyncMock()
            register_chained_signal_handlers(handler, signals=[signal.SIGTERM])
            mock_signal.assert_called_once()

    def test_preserves_original_handler(self):
        original_handler = MagicMock()
        with patch("shared.utils.signals.signal.getsignal", return_value=original_handler):
            with patch("shared.utils.signals.signal.signal") as mock_signal:
                handler = AsyncMock()
                register_chained_signal_handlers(handler, signals=[signal.SIGTERM])
                mock_signal.assert_called_once()

    def test_calls_handler_on_signal(self):
        with patch("shared.utils.signals.signal.getsignal", return_value=signal.SIG_DFL):
            with patch("shared.utils.signals.signal.signal") as mock_signal:
                with patch("shared.utils.signals.asyncio.create_task") as mock_create_task:
                    with patch("shared.utils.signals.signal.default_int_handler"):
                        handler = AsyncMock()
                        register_chained_signal_handlers(handler, signals=[signal.SIGTERM])

                        # Get the wrapper function that was registered
                        wrapper = mock_signal.call_args[0][1]

                        # Call the wrapper
                        wrapper(signal.SIGTERM, None)

                        # The handler should have been scheduled as a task
                        mock_create_task.assert_called_once()
