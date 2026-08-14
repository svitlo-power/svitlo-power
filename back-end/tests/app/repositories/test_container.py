"""Tests for app/repositories/container.py."""
from unittest.mock import MagicMock

from app.repositories.container import RepositoryContainer


class TestRepositoryContainer:
    def test_configure_binds_all_interfaces(self):
        container = RepositoryContainer()
        binder = MagicMock()
        container.configure(binder)

        # Verify that bind was called for each interface
        bind_calls = binder.bind.call_args_list
        assert len(bind_calls) > 0

        # Check that all expected interfaces are bound
        bound_interfaces = [call[0][0] for call in bind_calls]
        from app.repositories import (
            IMessagesRepository,
            IStationsRepository,
            IStationsDataRepository,
            IStationConnectionsRepository,
            IUsersRepository,
            IVisitsCounterRepository,
            ILookupsRepository,
            IBotsRepository,
            IChatsRepository,
            IExtDataRepository,
            IExtDeviceRepository,
            IDashboardRepository,
            ILoginHistoryRepository,
        )

        expected_interfaces = [
            IMessagesRepository,
            IStationsRepository,
            IStationsDataRepository,
            IStationConnectionsRepository,
            IUsersRepository,
            IVisitsCounterRepository,
            ILookupsRepository,
            IBotsRepository,
            IChatsRepository,
            IExtDataRepository,
            IExtDeviceRepository,
            IDashboardRepository,
            ILoginHistoryRepository,
        ]

        for interface in expected_interfaces:
            assert interface in bound_interfaces
