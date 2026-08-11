import sys
import asyncio
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the shared package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Suppress warnings from production code that we can't control
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine.*was never awaited")


@pytest.fixture(autouse=True)
def mock_beanie_collection():
    """Mock Beanie Document collection access so models can be instantiated without a DB."""
    from beanie import Document

    def mock_get_collection(self):
        return MagicMock()

    with patch.object(Document, "get_pymongo_collection", mock_get_collection):
        yield


@pytest.fixture(autouse=True)
def provide_event_loop():
    """Provide an event loop for synchronous tests that need asyncio.get_event_loop()."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_bounded_queue_notify():
    """Mock BoundedQueue._notify_async to prevent 'coroutine never awaited' warnings."""
    from shared.bounded_queue import BoundedQueue
    from unittest.mock import AsyncMock

    # Use AsyncMock which returns a coroutine when called.
    # The warning about "coroutine never awaited" is suppressed by the
    # warnings.filterwarnings above.
    with patch.object(BoundedQueue, "_notify_async", AsyncMock()):
        yield
