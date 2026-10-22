from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable

from beanie import PydanticObjectId

from app.settings import Settings
from .topics import (
    ANNOUNCEMENTS,
    BATTERY_LOW,
    EMERGENCY,
    OUTAGE_UPCOMING,
    POWER_STATUS,
    SCHEDULE_CHANGES,
)


# Trigger parameter keys stored in PushTemplate.params
LEAD_MINUTES = "lead_minutes"
DEBOUNCE_SECONDS = "debounce_seconds"
THRESHOLD = "threshold"
HYSTERESIS = "hysteresis"


@dataclass
class PushEvent:
    """An application event that becomes one notification per device language."""
    topic: str
    dedup_key: str
    # Template variables; LocalizableValue / {lang: text} values are resolved per device language
    context: dict[str, Any] = field(default_factory=dict)
    # Extra FCM data, e.g. buildingId or stationId
    data: dict[str, str] = field(default_factory=dict)
    # Short description for the delivery log
    summary: dict[str, str] = field(default_factory=dict)
    building_id: PydanticObjectId | None = None


@dataclass(frozen=True)
class EventParam:
    key: str
    min: int
    max: int
    default: Callable[[Settings], int]


@dataclass(frozen=True)
class EventDefinition:
    topic: str
    title: dict[str, str]
    body: dict[str, str]
    route: str
    # Sample variables for the template preview; keys also feed editor autocompletion
    sample: Callable[[], dict[str, Any]]
    params: list[EventParam] = field(default_factory=list)


def schedule_slot(start: int, end: int) -> dict[str, Any]:
    """Slot variables of the schedule templates; start/end are minutes from midnight."""
    return {
        "start": f"{start // 60:02d}:{start % 60:02d}",
        "end": f"{end // 60:02d}:{end % 60:02d}",
        "start_minutes": start,
        "end_minutes": end,
    }


def _building_sample() -> dict[str, Any]:
    return {
        "id": "6650f0c2a1b2c3d4e5f60718",
        "name": {"uk": "Будинок 1", "en": "Building 1"},
    }


EVENT_DEFINITIONS: list[EventDefinition] = [
    EventDefinition(
        topic=ANNOUNCEMENTS,
        title={"uk": "{{ announcement.title }}", "en": "{{ announcement.title }}"},
        body={"uk": "{{ announcement.body }}", "en": "{{ announcement.body }}"},
        route="/",
        sample=lambda: {
            "announcement": {
                "id": "6650f0c2a1b2c3d4e5f60719",
                "title": {"uk": "Планові роботи", "en": "Scheduled works"},
                "body": {"uk": "Завтра з 10:00 до 12:00 не працюватиме ліфт", "en": "The lift will be off tomorrow 10:00–12:00"},
            },
        },
    ),
    EventDefinition(
        topic=SCHEDULE_CHANGES,
        title={
            "uk": "{% if published %}Опубліковано графік на {{ date.strftime('%d.%m') }}"
                  "{% else %}Графік на {{ date.strftime('%d.%m') }} змінено{% endif %}",
            "en": "{% if published %}Schedule for {{ date.strftime('%d.%m') }} is published"
                  "{% else %}Schedule for {{ date.strftime('%d.%m') }} has changed{% endif %}",
        },
        body={
            "uk": "{% if slots %}Відключення: {% for s in slots %}{{ s.start }}–{{ s.end }}"
                  "{% if not loop.last %}, {% endif %}{% endfor %}{% else %}Відключень не заплановано{% endif %}",
            "en": "{% if slots %}Outages: {% for s in slots %}{{ s.start }}–{{ s.end }}"
                  "{% if not loop.last %}, {% endif %}{% endfor %}{% else %}No outages planned{% endif %}",
        },
        route="/schedule",
        sample=lambda: {
            "queue": "1.1",
            "day": "tomorrow",
            "date": date.today() + timedelta(days=1),
            "status": "ScheduleApplies",
            "published": True,
            "slots": [schedule_slot(8 * 60, 12 * 60), schedule_slot(18 * 60, 21 * 60)],
            "previous_slots": [],
        },
    ),
    EventDefinition(
        topic=OUTAGE_UPCOMING,
        title={
            "uk": "Відключення о {{ slot.start }}",
            "en": "Outage at {{ slot.start }}",
        },
        body={
            "uk": "Через {{ minutes_left }} хв світло вимкнуть за графіком до {{ slot.end }}",
            "en": "Power goes off in {{ minutes_left }} min as scheduled, until {{ slot.end }}",
        },
        route="/schedule",
        sample=lambda: {
            "queue": "1.1",
            "date": date.today(),
            "slot": schedule_slot(14 * 60, 18 * 60),
            "minutes_left": 30,
        },
        params=[
            EventParam(LEAD_MINUTES, 1, 24 * 60, lambda s: s.PUSH_OUTAGE_LEAD_MINUTES),
        ],
    ),
    EventDefinition(
        topic=EMERGENCY,
        title={
            "uk": "{% if active %}Аварійні відключення{% else %}Аварійні відключення скасовано{% endif %}",
            "en": "{% if active %}Emergency outages{% else %}Emergency outages are over{% endif %}",
        },
        body={
            "uk": "{% if active %}{{ date.strftime('%d.%m') }} діють аварійні відключення, графік не застосовується"
                  "{% else %}{{ date.strftime('%d.%m') }} знову діє графік відключень{% endif %}",
            "en": "{% if active %}Emergency outages on {{ date.strftime('%d.%m') }}, the schedule does not apply"
                  "{% else %}The outage schedule applies again on {{ date.strftime('%d.%m') }}{% endif %}",
        },
        route="/schedule",
        sample=lambda: {
            "queue": "1.1",
            "day": "today",
            "date": date.today(),
            "status": "EmergencyShutdowns",
            "previous_status": "ScheduleApplies",
            "active": True,
        },
    ),
    EventDefinition(
        topic=POWER_STATUS,
        title={
            "uk": "{{ building.name }}: {% if available %}світло є{% else %}світла немає{% endif %}",
            "en": "{{ building.name }}: {% if available %}power is back{% else %}power is out{% endif %}",
        },
        body={
            "uk": "{% if available %}Світло з’явилося{% else %}Світло зникло{% endif %} о {{ changed_at.strftime('%H:%M') }}",
            "en": "{% if available %}Power came back{% else %}Power went out{% endif %} at {{ changed_at.strftime('%H:%M') }}",
        },
        route="/buildings/{{ building.id }}",
        sample=lambda: {
            "building": _building_sample(),
            "available": False,
            "changed_at": datetime.now().replace(second=0, microsecond=0),
        },
        params=[
            EventParam(DEBOUNCE_SECONDS, 0, 3600, lambda s: s.PUSH_POWER_DEBOUNCE_SECONDS),
        ],
    ),
    EventDefinition(
        topic=BATTERY_LOW,
        title={
            "uk": "{{ building.name }}: низький заряд батареї",
            "en": "{{ building.name }}: battery is low",
        },
        body={
            "uk": "Заряд батареї станції {{ soc }}%",
            "en": "The station battery is at {{ soc }}%",
        },
        route="/buildings/{{ building.id }}",
        sample=lambda: {
            "building": _building_sample(),
            "station": {"id": "12345", "name": "Deye 1"},
            "soc": 18,
            "threshold": 20,
        },
        params=[
            EventParam(THRESHOLD, 1, 99, lambda s: s.PUSH_BATTERY_LOW_THRESHOLD),
            EventParam(HYSTERESIS, 1, 50, lambda s: s.PUSH_BATTERY_HYSTERESIS),
        ],
    ),
]


EVENTS_BY_TOPIC: dict[str, EventDefinition] = { d.topic: d for d in EVENT_DEFINITIONS }
