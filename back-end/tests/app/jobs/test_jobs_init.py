"""Tests for app/jobs/__init__.py."""
import os
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs import register_jobs


class TestRegisterJobs:
    def test_register_jobs_calls_load_and_register_modules(self):
        settings = MagicMock()
        injector = MagicMock()

        with patch("app.jobs.load_and_register_modules") as mock_load:
            register_jobs(settings, injector)
            mock_load.assert_called_once()

    def test_register_jobs_passes_correct_arguments(self):
        settings = MagicMock()
        injector = MagicMock()

        with patch("app.jobs.load_and_register_modules") as mock_load:
            register_jobs(settings, injector)
            args, kwargs = mock_load.call_args
            assert args[1] == "app.jobs"
            assert args[3] == settings
            assert args[4] == injector
            assert kwargs.get("register_method") is None or "register_method" not in kwargs

    def test_register_jobs_uses_correct_base_path(self):
        settings = MagicMock()
        injector = MagicMock()

        with patch("app.jobs.load_and_register_modules") as mock_load:
            register_jobs(settings, injector)
            args, _ = mock_load.call_args
            base_path = args[0]
            assert os.path.basename(base_path) == "jobs"
            assert os.path.exists(base_path)
