"""Event -> trigger -> PushEventDispatcher -> PushService -> mocked FcmSender, for every topic."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from beanie import PydanticObjectId

from app.models.api import AnnouncementRequest
from app.services.push.announcements import AnnouncementsService
from app.services.push.dispatcher import PushEventDispatcher
from app.services.push.events import PushEvent
from app.services.push.fcm_sender import FcmSendResult
from app.services.push.service import PushService
from app.services.push.templates import PushTemplatesService
from app.services.push.topics import (
    ANNOUNCEMENTS, BATTERY_LOW, DEFAULT_TOPICS, EMERGENCY, OUTAGE_UPCOMING, POWER_STATUS, SCHEDULE_CHANGES,
)
from app.services.push.triggers import BatteryPushTriggers, PowerPushTriggers, SchedulePushTriggers
from shared.models.assumed_station_status import AssumedStationStatus
from shared.models.localizable_value import LocalizableValue
from shared.models.push_delivery import PushDeliveryStatus
from shared.models.push_device import PushDevice, PushPlatform
from shared.models.push_topic import PushTopic
from shared.repositories.interfaces.push_devices import PushRecipient
from shared.services.outages_schedule import ScheduleUpdate
from shared.services.outages_schedule.models import DaySchedule, DayStatus, SchedulesResponse, Slot, SlotType, UnitSchedule


KYIV = ZoneInfo("Europe/Kyiv")
QUEUE = "1.1"


class _Devices:
    def __init__(self, devices):
        self.devices = devices

    async def get_topic_recipients(self, topic):
        return [
            PushRecipient(d.token, d.language)
            for d in self.devices if d.enabled and topic not in d.disabled_topics
        ]

    async def delete_devices(self, tokens):
        before = len(self.devices)
        self.devices = [d for d in self.devices if d.token not in tokens]
        return before - len(self.devices)


class _Deliveries:
    def __init__(self):
        self.items = {}

    async def try_insert(self, delivery):
        if delivery.dedup_key in self.items:
            return False
        delivery.id = PydanticObjectId()
        self.items[delivery.dedup_key] = delivery
        return True

    async def save(self, delivery):
        self.items[delivery.dedup_key] = delivery
        return delivery

    async def get_recent(self, limit):
        return list(self.items.values())[:limit]

    async def get_by_keys(self, keys):
        return [self.items[k] for k in keys if k in self.items]


class _States:
    def __init__(self):
        self.items = {}

    async def get_state(self, key):
        return self.items.get(key)

    async def set_state(self, key, data):
        self.items[key] = data


def _device(token, language="uk", **kwargs):
    return PushDevice(id=PydanticObjectId(), token=token, platform=PushPlatform.Android, language=language, **kwargs)


class _World:
    """Real push services wired with in-memory repositories and a mocked FCM sender."""

    def __init__(self, devices=None, invalid=()):
        settings = MagicMock()
        settings.BOT_TIMEZONE = "Europe/Kyiv"
        settings.PUSH_OUTAGE_LEAD_MINUTES = 30
        settings.PUSH_POWER_DEBOUNCE_SECONDS = 60
        settings.PUSH_BATTERY_LOW_THRESHOLD = 20
        settings.PUSH_BATTERY_HYSTERESIS = 10

        self.devices = _Devices(devices if devices is not None else [
            _device("tok-uk", "uk"),
            _device("tok-en", "en"),
            _device("tok-off", "uk", enabled=False),
            _device("tok-optout", "en", disabled_topics=[t.key for t in DEFAULT_TOPICS]),
        ])

        self.sender = MagicMock()
        self.sender.send = AsyncMock(side_effect=lambda tokens, message: FcmSendResult(
            success_count=len([t for t in tokens if t not in invalid]),
            failure_count=len([t for t in tokens if t in invalid]),
            invalid_tokens=[t for t in tokens if t in invalid],
        ))

        topics = MagicMock()
        topics.get_topic = AsyncMock(side_effect=lambda key: PushTopic(
            key=key, name=LocalizableValue({"en": key}), description=LocalizableValue({"en": key}),
        ))
        template_repo = MagicMock()
        template_repo.get_template = AsyncMock(return_value=None)

        self.deliveries = _Deliveries()
        self.templates = PushTemplatesService(template_repo, settings)
        self.push = PushService(self.devices, topics, self.sender)
        self.dispatcher = PushEventDispatcher(self.push, self.templates, topics, self.devices, self.deliveries)

    def sent(self):
        """{language-specific tokens: message} of every FCM call."""
        return { tuple(c.args[0]): c.args[1] for c in self.sender.send.await_args_list }

    def assert_sent_once(self, topic):
        sent = self.sent()
        assert set(sent) == {("tok-uk",), ("tok-en",)}
        assert self.sender.send.await_count == 2
        for message in sent.values():
            assert message.data["topic"] == topic
        [delivery] = self.deliveries.items.values()
        assert delivery.topic == topic
        assert delivery.status == PushDeliveryStatus.Sent
        assert delivery.recipients_by_language == {"uk": 1, "en": 1}
        return sent[("tok-uk",)], sent[("tok-en",)]


def _dashboard(buildings=(), queue=QUEUE):
    dashboard = MagicMock()
    dashboard.get_config = AsyncMock(return_value=SimpleNamespace(outages_schedule_queue=queue))
    dashboard.get_buildings = AsyncMock(return_value=list(buildings))
    return dashboard


def _schedule(day_date, slots=(), status=DayStatus.ScheduleApplies):
    return SchedulesResponse({QUEUE: UnitSchedule(
        days=[DaySchedule(
            date=datetime.combine(day_date, datetime.min.time(), tzinfo=KYIV),
            status=status,
            slots=[Slot(start=s, end=e, type=SlotType.Definite) for s, e in slots],
        )],
        updatedOn=datetime.now(timezone.utc),
    )})


def _building(station=None):
    return SimpleNamespace(
        id=PydanticObjectId(),
        name=LocalizableValue({"uk": "Будинок 7", "en": "Building 7"}),
        report_users=[SimpleNamespace(id=PydanticObjectId())],
        station=station,
    )


@pytest.mark.asyncio
async def test_announcement():
    world = _World()
    announcements_repo = MagicMock()
    announcements_repo.add = AsyncMock(side_effect=lambda a: setattr(a, "id", PydanticObjectId()) or a)
    service = AnnouncementsService(announcements_repo, world.deliveries, world.dispatcher)

    await service.publish(AnnouncementRequest(
        title={"uk": "Увага", "en": "Attention"}, body={"uk": "Текст", "en": "Text"},
    ))
    # Publishing sends in the background
    for task in list(PushEventDispatcher._tasks):
        await task

    uk, en = world.assert_sent_once(ANNOUNCEMENTS)
    assert (uk.title, uk.body) == ("Увага", "Текст")
    assert (en.title, en.body) == ("Attention", "Text")

    # The same announcement processed again is not sent twice
    [delivery] = world.deliveries.items.values()
    event_key = delivery.dedup_key
    assert event_key.startswith("announcement:")
    assert await world.dispatcher.dispatch(PushEvent(topic=ANNOUNCEMENTS, dedup_key=event_key)) is None
    assert world.sender.send.await_count == 2


@pytest.mark.asyncio
async def test_schedule_changes():
    world = _World()
    triggers = SchedulePushTriggers(world.dispatcher, world.templates, _dashboard(), MagicMock())
    today = datetime.now(KYIV).date()
    update = ScheduleUpdate(previous=_schedule(today, [(480, 720)]), current=_schedule(today, [(600, 720)]))

    await triggers.on_schedule_updated(update)
    await triggers.on_schedule_updated(update)

    uk, en = world.assert_sent_once(SCHEDULE_CHANGES)
    assert "10:00–12:00" in uk.body
    assert en.data["route"] == "/schedule"


@pytest.mark.asyncio
async def test_emergency():
    world = _World()
    triggers = SchedulePushTriggers(world.dispatcher, world.templates, _dashboard(), MagicMock())
    today = datetime.now(KYIV).date()
    update = ScheduleUpdate(
        previous=_schedule(today, [(480, 720)]),
        current=_schedule(today, status=DayStatus.EmergencyShutdowns),
    )

    await triggers.on_schedule_updated(update)
    await triggers.on_schedule_updated(update)

    uk, en = world.assert_sent_once(EMERGENCY)
    assert uk.title == "Аварійні відключення"
    assert en.title == "Emergency outages"


@pytest.mark.asyncio
async def test_outage_upcoming():
    world = _World()
    now = datetime.now(KYIV).replace(second=0, microsecond=0)
    start = now + timedelta(minutes=15)
    minutes = start.hour * 60 + start.minute
    if minutes + 60 > 24 * 60:
        pytest.skip("Too close to midnight for a same-day slot")
    outages = MagicMock()
    outages.get_schedule_async = AsyncMock(return_value=_schedule(start.date(), [(minutes, minutes + 60)]))
    triggers = SchedulePushTriggers(world.dispatcher, world.templates, _dashboard(), outages)

    await triggers.check_upcoming(now)
    await triggers.check_upcoming(now + timedelta(minutes=1))

    uk, en = world.assert_sent_once(OUTAGE_UPCOMING)
    assert f"{start:%H:%M}" in uk.title
    assert "15" in en.body


@pytest.mark.asyncio
async def test_power_status():
    world = _World()
    building = _building()
    lost_at = datetime(2026, 10, 22, 7, 0, tzinfo=timezone.utc)
    report = {"state": True, "at": lost_at - timedelta(hours=1)}
    ext_data = MagicMock()
    ext_data.get_last_ext_data_by_user_id = AsyncMock(
        side_effect=lambda _: SimpleNamespace(grid_state=report["state"], received_at=report["at"])
    )

    def triggers(states):
        return PowerPushTriggers(world.dispatcher, world.templates, _dashboard([building]), ext_data, states)

    first_instance, second_instance = _States(), _States()
    for states in (first_instance, second_instance):
        await triggers(states).check(lost_at - timedelta(minutes=30))
    report.update(state=False, at=lost_at)
    for states in (first_instance, second_instance):
        # Both instances see the same change after the debounce time
        await triggers(states).check(lost_at + timedelta(seconds=90))

    uk, en = world.assert_sent_once(POWER_STATUS)
    assert uk.title == "Будинок 7: світла немає"
    assert en.title == "Building 7: power is out"
    assert "10:00" in en.body  # local time in Kyiv
    assert en.data["buildingId"] == str(building.id)
    assert en.data["route"] == f"/buildings/{building.id}"
    [delivery] = world.deliveries.items.values()
    assert delivery.building_id == building.id


@pytest.mark.asyncio
async def test_battery_low():
    world = _World()
    station = SimpleNamespace(
        id=PydanticObjectId(), station_id=1, station_name="Deye",
        station_alias=LocalizableValue({"uk": "Станція", "en": "Station"}),
        enabled=True, connection_status="NORMAL",
    )
    building = _building(station=station)
    stations_data = MagicMock()
    stations_data.get_assumed_connection_status = AsyncMock(return_value=AssumedStationStatus.NORMAL)
    stations_data.get_last_station_data = AsyncMock(return_value=SimpleNamespace(
        battery_soc=17.6, last_update_time=datetime(2026, 10, 22, 7, 0),
    ))

    for states in (_States(), _States()):
        await BatteryPushTriggers(
            world.dispatcher, world.templates, _dashboard([building]), stations_data, states,
        ).check()

    uk, en = world.assert_sent_once(BATTERY_LOW)
    assert "18%" in uk.body
    assert en.title == "Building 7: battery is low"
    assert en.data["stationId"] == str(station.id)


@pytest.mark.asyncio
async def test_invalid_tokens_are_removed():
    world = _World(invalid={"tok-en"})
    triggers = SchedulePushTriggers(world.dispatcher, world.templates, _dashboard(), MagicMock())
    today = datetime.now(KYIV).date()

    await triggers.on_schedule_updated(ScheduleUpdate(
        previous=_schedule(today, [(480, 720)]), current=_schedule(today, [(600, 720)]),
    ))

    [delivery] = world.deliveries.items.values()
    assert delivery.success_count == 1
    assert delivery.failure_count == 1
    assert delivery.invalid_removed == 1
    assert "tok-en" not in [d.token for d in world.devices.devices]
