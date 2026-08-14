"""Tests for app/services/message_generator/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.message_generator.service import MessageGeneratorService
from app.services.message_generator.models import MessageGeneratorConfig
from app.services.interfaces import MessageItem
from app.repositories import IMessagesRepository, IStationsDataRepository
from shared.models.message import Message
from shared.models.station import Station
from shared.models.station_data import StationData
from shared.models.localizable_value import LocalizableValue


class TestMessageGeneratorServiceInit:
    def test_init_stores_dependencies(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)
        assert service._messages is mock_messages_repo
        assert service._stations_data is mock_stations_data_repo
        assert service._injector is mock_injector

    def test_init_with_invalid_timezone_falls_back_to_utc(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "Invalid/Timezone"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)
        assert service._message_timezone is not None


class TestMessageGeneratorServiceGenerateMessage:
    @pytest.mark.asyncio
    async def test_generate_message_all_stations_disabled_returns_none(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=False)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        result = await service.generate_message(message)
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_message_single_disabled_station_returns_none(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=False)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        result = await service.generate_message(message)
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_message_returns_message_item(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=None)

        result = await service.generate_message(message)
        assert result is not None
        assert isinstance(result, MessageItem)
        assert result.message == "Hello"
        assert result.should_send is True
        assert result.timeout == 300

    @pytest.mark.asyncio
    async def test_generate_message_with_include_data(self):
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=None)

        result = await service.generate_message(message, include_data=True)
        assert result is not None
        assert result.data is not None
        assert "stations" in result.data

    @pytest.mark.asyncio
    async def test_generate_message_with_station_alias(self):
        """Test generate_message with station_alias set."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        station.station_alias = LocalizableValue({"en": "Alias"})
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=None)

        result = await service.generate_message(message)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_message_with_station_data(self):
        """Test generate_message with station data (covers _add_methods with current)."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_message_single_station_with_data(self):
        """Test generate_message with single station and data (covers station template_data)."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_message_with_last_sent_time(self):
        """Test generate_message with last_sent_time set."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="Hello", should_send_template="True", timeout_template="300",
                          stations=[station])
        message.last_sent_time = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=None)

        result = await service.generate_message(message)
        assert result is not None
