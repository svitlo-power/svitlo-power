"""Shared pytest fixtures for back-end tests."""
import sys
import asyncio
import warnings
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Ensure the back-end app and shared package are importable
BACKEND_ROOT = Path(__file__).resolve().parent.parent
SHARED_ROOT = BACKEND_ROOT.parent / "shared" / "python"

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SHARED_ROOT))

# Suppress warnings from production code that we can't control
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine.*was never awaited")


@pytest.fixture(autouse=True)
def mock_beanie_collection():
    """Mock Beanie Document collection access so models can be instantiated without a DB."""
    from beanie import Document

    def mock_get_collection(self):
        return MagicMock()

    def mock_get_settings(cls):
        settings = MagicMock()
        settings.use_state_management = False
        return settings

    with patch.object(Document, "get_pymongo_collection", mock_get_collection), \
         patch.object(Document, "get_settings", classmethod(mock_get_settings)):
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

    with patch.object(BoundedQueue, "_notify_async", AsyncMock()):
        yield


@pytest.fixture
def mock_settings():
    """Provide a mock Settings object for tests that need it."""
    from app.settings import Settings

    settings = MagicMock(spec=Settings)
    settings.SECRET_KEY = "test-secret-key-for-testing-only-32chars!"
    settings.JWT_SECRET_KEY = "test-jwt-secret-key-for-testing-only-64chars!!"
    settings.JWT_ACCESS_TOKEN_EXPIRES_MIN = 60
    settings.JWT_REFRESH_TOKEN_EXPIRES_MIN = 60 * 24 * 7
    settings.DEBUG = True
    settings.HOST = "127.0.0.1"
    settings.STATISTIC_KEEP_DAYS = 3
    settings.SSE_PING_INTERVAL = 45
    settings.DEYE_FETCH_INTERVAL = 120
    settings.DEYE_SYNC_STATIONS_ON_POLL = False
    settings.DEYE_REPORT_INTERVAL = 300
    settings.DEYE_ASSUMED_OFFLINE_REPORTS = 2
    settings.TG_HOOK_BASE_URL = "https://example.com"
    settings.BOT_TIMEZONE = "utc"
    settings.ADMIN_USER = None
    settings.ADMIN_PASSWORD = None
    settings.DEYE_BASE_URL = None
    settings.DEYE_APP_ID = None
    settings.DEYE_APP_SECRET = None
    settings.DEYE_EMAIL = None
    settings.DEYE_PASSWORD = None
    settings.MONGO_URI = "mongodb://localhost:27017"
    settings.MONGO_DB = "test-db"
    settings.REDIS_URI = "redis://localhost:6379"
    settings.I18N_PATH = "../shared/i18n"
    return settings


@pytest.fixture
def mock_events_service():
    """Provide a mock EventsService."""
    from shared.services.events.service import EventsService

    events = MagicMock(spec=EventsService)
    events.broadcast_public = AsyncMock()
    events.broadcast_private = AsyncMock()
    events.add_public_client = MagicMock()
    events.add_private_client = MagicMock()
    events.remove_client = MagicMock()
    return events
