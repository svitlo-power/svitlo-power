import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import aiohttp

from shared.services.outages_schedule.service import OutagesScheduleService
from shared.services.events.service import EventsService
from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository
from shared.services.outages_schedule.models import SchedulesResponse, UnitSchedule, DaySchedule, Slot, SlotType, DayStatus


@pytest.fixture
def mock_events_service():
    return AsyncMock(spec=EventsService)


@pytest.fixture
def mock_aiohttp_session():
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_outages_repo():
    return AsyncMock(spec=IOutagesScheduleRepository)


@pytest.fixture
def outages_service(mock_events_service, mock_aiohttp_session, mock_outages_repo):
    return OutagesScheduleService(
        events=mock_events_service,
        session=mock_aiohttp_session,
        repository=mock_outages_repo,
    )


@pytest.fixture
def sample_schedule():
    return SchedulesResponse(
        root={
            "queue_1": UnitSchedule(
                days=[
                    DaySchedule(
                        slots=[Slot(start=0, end=24, type=SlotType.Definite)],
                        date=datetime.now(timezone.utc),
                        status=DayStatus.ScheduleApplies,
                    ),
                ],
                updatedOn=datetime.now(timezone.utc),
            )
        }
    )


class TestOutagesScheduleService:
    @pytest.mark.asyncio
    async def test_fetch_yasno_json_uses_json_request_defaults(
        self, outages_service, mock_aiohttp_session,
    ):
        response = MagicMock()
        response.__aenter__ = AsyncMock(return_value=response)
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(return_value={"ok": True})
        mock_aiohttp_session.get = MagicMock(return_value=response)

        result = await outages_service._fetch_yasno_json("https://yasno.example/data")

        assert result == {"ok": True}
        request_args = mock_aiohttp_session.get.call_args
        assert request_args.args == ("https://yasno.example/data",)
        assert request_args.kwargs["timeout"] == 10
        assert request_args.kwargs["headers"]["Accept"] == "application/json"
        response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_regions_normalizes_supported_payload_shapes(self, outages_service):
        outages_service._fetch_yasno_json = AsyncMock(return_value={
            "regions": [
                {
                    "id": "25",
                    "value": "Kyiv",
                    "dsos": [
                        {"id": "902", "name": "Yasno"},
                        {"dsoId": "903", "value": "Other"},
                        {"id": None, "name": "Missing id"},
                        "not a provider",
                    ],
                },
                {
                    "regionId": 26,
                    "regionName": "Lviv",
                    "providers": [{"dsoId": 904, "value": "Lviv DSO"}],
                },
                {"id": 27},
                None,
            ],
        })

        result = await outages_service.fetch_regions()

        assert result == [
            {
                "id": 25,
                "value": "Kyiv",
                "label": "Kyiv",
                "dsos": [
                    {"id": 902, "name": "Yasno"},
                    {"id": 903, "name": "Other"},
                ],
            },
            {
                "id": 26,
                "value": "Lviv",
                "label": "Lviv",
                "dsos": [{"id": 904, "name": "Lviv DSO"}],
            },
        ]
        assert outages_service._regions == result

    @pytest.mark.asyncio
    async def test_fetch_regions_rejects_unexpected_payload(self, outages_service):
        outages_service._fetch_yasno_json = AsyncMock(return_value={"regions": "invalid"})

        with pytest.raises(ValueError, match="Unexpected regions response"):
            await outages_service.fetch_regions()

    @pytest.mark.asyncio
    async def test_fetch_providers_loads_regions_and_reports_unknown_region(self, outages_service):
        outages_service._fetch_yasno_json = AsyncMock(return_value=[
            {"id": 25, "value": "Kyiv", "dsos": [{"id": 902, "name": "Yasno"}]},
        ])

        assert await outages_service.fetch_providers_for_region("Kyiv") == [
            {"id": 902, "name": "Yasno"},
        ]
        outages_service._fetch_yasno_json.assert_awaited_once()

        with pytest.raises(KeyError, match="Unknown YASNO region"):
            await outages_service.fetch_providers_for_region("Missing")

    @pytest.mark.asyncio
    async def test_get_providers_requires_regions_to_be_fetched(self, outages_service):
        with pytest.raises(RuntimeError, match="Regions have not been fetched"):
            outages_service.get_providers_for_region("Kyiv")

    @pytest.mark.asyncio
    async def test_fetch_queues_supports_object_and_list_payloads(self, outages_service):
        outages_service._fetch_yasno_json = AsyncMock(return_value={"1.1": {}, "1.2": {}})
        assert await outages_service.fetch_queues(25, 902) == ["1.1", "1.2"]

        outages_service._fetch_yasno_json = AsyncMock(return_value=[
            {"name": "2.1"},
            {"value": "2.2"},
            {"name": ""},
            None,
        ])
        assert await outages_service.fetch_queues(25, 902) == ["2.1", "2.2"]

    @pytest.mark.asyncio
    async def test_fetch_queues_rejects_unexpected_payload(self, outages_service):
        outages_service._fetch_yasno_json = AsyncMock(return_value="invalid")

        with pytest.raises(ValueError, match="Unexpected queues response"):
            await outages_service.fetch_queues(25, 902)

    @pytest.mark.asyncio
    async def test_get_schedule_async(self, outages_service, mock_outages_repo, sample_schedule):
        mock_outages_repo.get_schedule.return_value = sample_schedule
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is not None
        assert "queue_1" in result.root
        mock_outages_repo.get_schedule.assert_called_once_with("queue_1")

    @pytest.mark.asyncio
    async def test_get_schedule_async_not_found(self, outages_service, mock_outages_repo):
        mock_outages_repo.get_schedule.return_value = None
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is None
        mock_outages_repo.get_schedule.assert_called_once_with("queue_1")

    @pytest.mark.asyncio
    async def test_get_schedule_sync_not_running_loop(self, outages_service, mock_outages_repo, sample_schedule):
        mock_outages_repo.get_schedule.return_value = sample_schedule
        
        # Mock asyncio.get_event_loop to return a non-running loop
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.return_value = sample_schedule
            mock_get_loop.return_value = mock_loop
            
            result = outages_service.get_schedule("queue_1")
            
            assert result is not None
            assert "queue_1" in result.root

    @pytest.mark.asyncio
    async def test_get_schedule_sync_running_loop(self, outages_service):
        # Mock asyncio.get_event_loop to return a running loop
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            
            result = outages_service.get_schedule("queue_1")
            
            assert result is None

    def test_get_schedule_sync_without_event_loop(self, outages_service):
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no event loop")):
            assert outages_service.get_schedule("queue_1") is None

    @pytest.mark.asyncio
    async def test_update_success(self, outages_service, mock_aiohttp_session, mock_outages_repo, mock_events_service):
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "queue_1": {
                "today": {"date": "2024-01-15T00:00:00Z", "slots": [{"start": 0, "end": 24, "type": "Definite"}], "status": "ScheduleApplies"},
                "tomorrow": {"date": "2024-01-16T00:00:00Z", "slots": [{"start": 0, "end": 24, "type": "Definite"}], "status": "ScheduleApplies"},
                "updatedOn": "2024-01-15T10:00:00Z"
            }
        }
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        # Mock repository set_schedule
        mock_outages_repo.set_schedule = AsyncMock()
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None  # update returns None on success
        mock_aiohttp_session.get.assert_called_once()
        mock_outages_repo.set_schedule.assert_called_once()
        mock_events_service.broadcast_public.assert_called_once_with("outages_updated", None)

    @pytest.mark.asyncio
    async def test_update_http_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_connection_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        import aiohttp
        mock_aiohttp_session.get.side_effect = aiohttp.ClientConnectionError("Connection failed")
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_client_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_aiohttp_session.get.side_effect = aiohttp.ClientError("request failed")

        result = await outages_service.update(region=1, dso=1)

        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_timeout(self, outages_service, mock_aiohttp_session, mock_events_service):
        import asyncio
        mock_aiohttp_session.get.side_effect = asyncio.TimeoutError()
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "queue_1": {
                "today": {"date": "not a date", "slots": []},
            },
        }
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_generic_exception(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_aiohttp_session.get.side_effect = Exception("Unexpected error")
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])