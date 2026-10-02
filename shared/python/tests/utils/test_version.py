"""Tests for shared/utils/version.py."""
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from shared.utils.version import get_version


class TestGetVersion:
    def test_get_version_reads_from_file(self):
        """Test that get_version reads version from /app/VERSION file."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="2026.10.01\n"):
                result = get_version()
                assert result == "2026.10.01"

    def test_get_version_strips_whitespace(self):
        """Test that get_version strips whitespace from version string."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="  2026.10.01  \n"):
                result = get_version()
                assert result == "2026.10.01"

    def test_get_version_returns_default_when_file_not_exists(self):
        """Test that get_version returns default when VERSION file does not exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = get_version()
            assert result == "0000.00.00"

    def test_get_version_returns_default_on_exception(self):
        """Test that get_version returns default when reading fails."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
                result = get_version()
                assert result == "0000.00.00"

    def test_get_version_returns_default_on_permission_error(self):
        """Test that get_version returns default on PermissionError."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                result = get_version()
                assert result == "0000.00.00"

    def test_get_version_handles_empty_file(self):
        """Test that get_version returns default when file is empty."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=""):
                result = get_version()
                assert result == "0000.00.00"

    def test_get_version_handles_only_whitespace(self):
        """Test that get_version returns default when file contains only whitespace."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="   \n\t  "):
                result = get_version()
                assert result == "0000.00.00"