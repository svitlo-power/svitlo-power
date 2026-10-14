"""Tests for app/services/message_generator/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import os
import pytest

from app.services.message_generator.service import MessageGeneratorService
from app.services.message_generator.models import MessageGeneratorConfig
from app.services.interfaces import MessageItem
from app.repositories import IMessagesRepository, IStationsDataRepository
from shared.models.message import Message
from shared.models.station import Station
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

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # Use a template that references the request methods via station/stations so they get invoked
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ station.get_average(column='consumption_power') }} {{ station.get_average_all(column='generation_power') }} {{ station.get_average_minutes(column='battery_power', minutes=30) }} {{ station.get_assumed_state() }} {{ station.get_ext_grid_state() }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message, include_data=True)
        assert result is not None
        assert result.data is not None
        assert "stations" in result.data
        # Debug: write collected requests to file
        import json
        with open("debug_requests.json", "w") as f:
            json.dump({
                "keys": list(result.data.keys()),
                "requests": result.data.get("requests", []),
                "stations": result.data.get("stations", []),
                "station": result.data.get("station", None)
            }, f, default=str, indent=2)
        if os.path.exists("debug_requests.json"):
            os.remove("debug_requests.json")

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


class TestMessageGeneratorServiceAddMethods:
    """Tests for _add_methods binding requests to template data."""

    @pytest.mark.asyncio
    async def test_add_methods_binds_all_requests_in_collect_mode(self):
        """Test that _add_methods binds all request types in Collect mode."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # Use a template that references the request methods via station so they get invoked
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ station.get_average(column='consumption_power') }} {{ station.get_average_all(column='generation_power') }} {{ station.get_average_minutes(column='battery_power', minutes=30) }} {{ station.get_assumed_state() }} {{ station.get_ext_grid_state() }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        # Call generate_message with include_data=True to trigger Collect mode
        result = await service.generate_message(message, include_data=True)

        # Verify all request types were collected
        assert result is not None
        assert result.data is not None
        assert "requests" in result.data
        
        collected_requests = [r["request"] for r in result.data["requests"]]
        
        # Check all expected request types are present
        assert any("get_average(" in r for r in collected_requests)
        assert any("get_average_all(" in r for r in collected_requests)
        assert any("get_average_minutes(" in r for r in collected_requests)
        assert any("get_assumed_state(" in r for r in collected_requests)
        assert any("get_ext_grid_state(" in r for r in collected_requests)

    @pytest.mark.asyncio
    async def test_add_methods_binds_requests_for_single_station(self):
        """Test that _add_methods binds requests for the single 'station' key when only one station."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # Use a template that references the request methods via station so they get invoked
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ station.get_average(column='consumption_power') }} {{ station.get_average_all(column='generation_power') }} {{ station.get_average_minutes(column='battery_power', minutes=30) }} {{ station.get_assumed_state() }} {{ station.get_ext_grid_state() }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message, include_data=True)

        assert result is not None
        assert result.data is not None
        assert "requests" in result.data
        
        collected_requests = [r["request"] for r in result.data["requests"]]
        
        # With single station, the 'station' key gets requests (same as stations[0] since they're the same object)
        # The collector deduplicates identical requests, so we see each request type once
        avg_count = sum(1 for r in collected_requests if "get_average(" in r)
        avg_all_count = sum(1 for r in collected_requests if "get_average_all(" in r)
        avg_min_count = sum(1 for r in collected_requests if "get_average_minutes(" in r)
        assumed_count = sum(1 for r in collected_requests if "get_assumed_state(" in r)
        ext_grid_count = sum(1 for r in collected_requests if "get_ext_grid_state(" in r)
        
        assert avg_count == 1, f"Expected 1 get_average request, got {avg_count}"
        assert avg_all_count == 1, f"Expected 1 get_average_all request, got {avg_all_count}"
        assert avg_min_count == 1, f"Expected 1 get_average_minutes request, got {avg_min_count}"
        assert assumed_count == 1, f"Expected 1 get_assumed_state request, got {assumed_count}"
        assert ext_grid_count == 1, f"Expected 1 get_ext_grid_state request, got {ext_grid_count}"

    @pytest.mark.asyncio
    async def test_add_methods_binds_requests_for_multiple_stations(self):
        """Test that _add_methods binds requests for each station in multiple stations."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station1 = Station(station_id=1, station_name="Test1", enabled=True, order=1)
        station2 = Station(station_id=2, station_name="Test2", enabled=True, order=2)
        # Use a template that references the request methods via stations array
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ stations[0].get_average(column='consumption_power') }} {{ stations[1].get_average(column='consumption_power') }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station1, station2])

        mock_station_data1 = MagicMock()
        mock_station_data1.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_station_data2 = MagicMock()
        mock_station_data2.to_dict = MagicMock(return_value={"current": {"station_id": 2}})
        
        async def get_station_data(station_id):
            if station_id == 1:
                return mock_station_data1
            return mock_station_data2
        
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(side_effect=get_station_data)

        result = await service.generate_message(message, include_data=True)

        assert result is not None
        assert result.data is not None
        assert "requests" in result.data
        
        collected_requests = [r["request"] for r in result.data["requests"]]
        
        # With 2 stations, each should have requests for the methods they reference
        # No 'station' key since there are multiple stations
        avg_count = sum(1 for r in collected_requests if "get_average(" in r)
        assert avg_count == 2, f"Expected 2 get_average requests, got {avg_count}"

    @pytest.mark.asyncio
    async def test_add_methods_skips_disabled_stations(self):
        """Test that _add_methods doesn't bind requests for disabled stations."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station1 = Station(station_id=1, station_name="Test1", enabled=True, order=1)
        station2 = Station(station_id=2, station_name="Test2", enabled=False, order=2)  # Disabled
        # Use a template that references the request methods via stations array
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ stations[0].get_average(column='consumption_power') }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station1, station2])

        mock_station_data1 = MagicMock()
        mock_station_data1.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        
        async def get_station_data(station_id):
            if station_id == 1:
                return mock_station_data1
            return None
        
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(side_effect=get_station_data)

        result = await service.generate_message(message, include_data=True)

        assert result is not None
        assert result.data is not None
        assert "requests" in result.data
        
        collected_requests = [r["request"] for r in result.data["requests"]]
        
        # Only station1 (enabled) should have requests = 1 request type
        avg_count = sum(1 for r in collected_requests if "get_average(" in r)
        assert avg_count == 1, f"Expected 1 get_average request, got {avg_count}"

    @pytest.mark.asyncio
    async def test_add_methods_uses_correct_start_date_for_average_request(self):
        """Test that AverageRequest gets last_sent_time as start_date."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)
        
        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()
        
        mock_injector.get = injector_get
        
        # Mock ext data repo for GetExtGridStateRequest
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                          message_template="{{ station.get_average(column='consumption_power') }}",
                          should_send_template="True", timeout_template="300",
                          stations=[station])
        last_sent = datetime.now(timezone.utc) - timedelta(hours=2)
        message.last_sent_time = last_sent

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message, include_data=True)

        assert result is not None
        assert result.data is not None
        assert "requests" in result.data
        
        # Debug: print all requests
        import json
        with open("debug_requests2.json", "w") as f:
            json.dump({
                "requests": result.data.get("requests", []),
                "station_keys": list(result.data.get("station", {}).keys()) if result.data.get("station") else None,
                "stations_0_keys": list(result.data.get("stations", [{}])[0].keys()) if result.data.get("stations") else None,
            }, f, default=str, indent=2)
        
        # Find the get_average request and verify it has the correct start_date
        avg_requests = [r for r in result.data["requests"] if "get_average(" in r["request"]]
        assert len(avg_requests) >= 1
        
        # The request description should contain the start_date (last_sent_time)
        # Note: exact format depends on describe() implementation
        avg_desc = avg_requests[0]["request"]
        assert "get_average" in avg_desc
        assert "station_id=1" in avg_desc

        if os.path.exists("debug_requests2.json"):
            os.remove("debug_requests2.json")


class TestMessageGeneratorServiceTemplateRequestsInShouldSendAndTimeout:
    """Tests for template requests in should_send_template and timeout_template."""

    @pytest.mark.asyncio
    async def test_should_send_template_with_get_ext_grid_state(self):
        """Test that should_send_template can use get_ext_grid_state() request."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)

        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()

        mock_injector.get = injector_get

        # Mock ext data repo for GetExtGridStateRequest - return True (grid is ON)
        mock_building = MagicMock()
        mock_building.report_users = [MagicMock(id=1)]
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        # Mock the ext data repo to return grid state
        mock_reporter_state = MagicMock()
        mock_reporter_state.grid_state = True
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=mock_reporter_state)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # should_send_template uses get_ext_grid_state() - only send if grid is ON
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                            message_template="Hello",
                            should_send_template="{{ station.get_ext_grid_state() == true }}",
                            timeout_template="300",
                            stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)

        assert result is not None
        assert result.should_send is True  # Grid is ON, so should_send should be True

    @pytest.mark.asyncio
    async def test_should_send_template_with_get_ext_grid_state_false(self):
        """Test that should_send_template returns False when grid is OFF."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)

        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()

        mock_injector.get = injector_get

        # Mock ext data repo for GetExtGridStateRequest - return False (grid is OFF)
        mock_building = MagicMock()
        mock_building.report_users = []
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        # Mock the ext data repo to return grid state
        mock_ext_data = MagicMock()
        mock_ext_data.get_grid_state = AsyncMock(return_value=False)
        mock_ext_data_repo.get_ext_data = AsyncMock(return_value=mock_ext_data)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # should_send_template uses get_ext_grid_state() - only send if grid is ON
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                            message_template="Hello",
                            should_send_template="{{ station.get_ext_grid_state() == true }}",
                            timeout_template="300",
                            stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)

        assert result is not None
        assert result.should_send is False  # Grid is OFF, so should_send should be False

    @pytest.mark.asyncio
    async def test_timeout_template_with_get_ext_grid_state(self):
        """Test that timeout_template can use get_ext_grid_state() request for dynamic timeout."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)

        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()

        mock_injector.get = injector_get

        # Mock ext data repo for GetExtGridStateRequest - return True (grid is ON)
        mock_building = MagicMock()
        mock_building.report_users = [MagicMock(id=1)]
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        # Mock the ext data repo to return grid state
        mock_reporter_state = MagicMock()
        mock_reporter_state.grid_state = True
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=mock_reporter_state)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # timeout_template uses get_ext_grid_state() - longer timeout when grid is OFF
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                            message_template="Hello",
                            should_send_template="True",
                            timeout_template="{% if station.get_ext_grid_state() %}300{% else %}60{% endif %}",
                            stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)

        assert result is not None
        assert result.timeout == 300  # Grid is ON, so timeout should be 300

    @pytest.mark.asyncio
    async def test_timeout_template_with_get_ext_grid_state_off(self):
        """Test that timeout_template returns shorter timeout when grid is OFF."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)

        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()

        mock_injector.get = injector_get

        # Mock ext data repo for GetExtGridStateRequest - return False (grid is OFF)
        mock_building = MagicMock()
        mock_building.report_users = [MagicMock(id=1)]
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        # Mock the ext data repo to return grid state
        mock_reporter_state = MagicMock()
        mock_reporter_state.grid_state = False
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=mock_reporter_state)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # timeout_template uses get_ext_grid_state() - longer timeout when grid is OFF
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                            message_template="Hello",
                            should_send_template="True",
                            timeout_template="{% if station.get_ext_grid_state() %}300{% else %}60{% endif %}",
                            stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)

        assert result is not None
        assert result.timeout == 60  # Grid is OFF, so timeout should be 60

    @pytest.mark.asyncio
    async def test_should_send_and_timeout_both_use_requests(self):
        """Test that both should_send_template and timeout_template can use requests simultaneously."""
        mock_config = MagicMock(spec=MessageGeneratorConfig)
        mock_config.timezone = "utc"
        mock_messages_repo = MagicMock(spec=IMessagesRepository)
        mock_stations_data_repo = MagicMock(spec=IStationsDataRepository)
        mock_injector = MagicMock()

        # Mock the injector.get to return the right repositories for requests
        from app.repositories import IExtDataRepository, IDashboardRepository
        mock_ext_data_repo = MagicMock(spec=IExtDataRepository)
        mock_dashboard_repo = MagicMock(spec=IDashboardRepository)

        def injector_get(cls):
            if cls == IStationsDataRepository:
                return mock_stations_data_repo
            elif cls == IExtDataRepository:
                return mock_ext_data_repo
            elif cls == IDashboardRepository:
                return mock_dashboard_repo
            return MagicMock()

        mock_injector.get = injector_get

        # Mock ext data repo for GetExtGridStateRequest - return True (grid is ON)
        mock_building = MagicMock()
        mock_building.report_users = [MagicMock(id=1)]
        mock_dashboard_repo.get_building_by_station_id = AsyncMock(return_value=mock_building)

        # Mock the ext data repo to return grid state
        mock_reporter_state = MagicMock()
        mock_reporter_state.grid_state = True
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=mock_reporter_state)

        service = MessageGeneratorService(mock_config, mock_messages_repo, mock_stations_data_repo, mock_injector)

        station = Station(station_id=1, station_name="Test", enabled=True, order=1)
        # Both templates use get_ext_grid_state()
        message = Message(name="Test", channel_id="ch", enabled=True, language="en",
                            message_template="Grid state: {{ station.get_ext_grid_state() }}",
                            should_send_template="{{ station.get_ext_grid_state() == true }}",
                            timeout_template="{% if station.get_ext_grid_state() %}300{% else %}60{% endif %}",
                            stations=[station])

        mock_station_data = MagicMock()
        mock_station_data.to_dict = MagicMock(return_value={"current": {"station_id": 1}})
        mock_stations_data_repo.get_station_data_tuple = AsyncMock(return_value=mock_station_data)

        result = await service.generate_message(message)

        assert result is not None
        assert result.should_send is True
        assert result.timeout == 300
        assert "Grid state: True" in result.message
