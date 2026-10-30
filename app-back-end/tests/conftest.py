"""Pytest configuration for app-back-end tests."""
import pytest
from shared.features import feature_flags, FeatureFlag


def pytest_configure(config):
    """Enable required feature flags for tests."""
    # Enable feature flags needed for app-back-end tests
    feature_flags.set_enabled(FeatureFlag.APP_BACKEND_REDIS_READS, True)
    feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
    feature_flags.set_enabled(FeatureFlag.BACKEND_SSE_REDIS, True)
    feature_flags.set_enabled(FeatureFlag.APP_BACKEND_SSE_REDIS, True)