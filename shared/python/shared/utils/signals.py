import asyncio
import os
import signal
from collections.abc import Callable
from typing import Iterable, Awaitable


AsyncSignalHandler = Callable[[int], Awaitable[None]]

def register_chained_signal_handlers(
    handler: AsyncSignalHandler,
    signals: Iterable[int] | None = None,
) -> None:
    if signals is None:
        if os.name != "nt":
            signals = (signal.SIGINT, signal.SIGTERM)
        else:
            # SIGBREAK is Windows-specific; fallback to SIGTERM if not available
            sigbreak = getattr(signal, "SIGBREAK", signal.SIGTERM)
            signals = (signal.SIGINT, sigbreak)

    for sig in signals:
        original_handler = signal.getsignal(sig)

        def make_handler(original):
            def wrapper(signum, frame):
                asyncio.create_task(handler(signum))

                if callable(original):
                    original(signum, frame)
                elif original == signal.SIG_DFL:
                    signal.default_int_handler(signum, frame)

            return wrapper

        signal.signal(sig, make_handler(original_handler))
