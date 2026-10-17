from dataclasses import dataclass


@dataclass(frozen=True)
class TopicDefinition:
    key: str
    name: dict[str, str]
    description: dict[str, str]


ANNOUNCEMENTS = "announcements"
SCHEDULE_CHANGES = "schedule_changes"
OUTAGE_UPCOMING = "outage_upcoming"
EMERGENCY = "emergency"
POWER_STATUS = "power_status"
BATTERY_LOW = "battery_low"


# Built-in topics. They are created on start; admins can turn them on and off but not remove them,
# because triggers in code send to these keys.
DEFAULT_TOPICS: list[TopicDefinition] = [
    TopicDefinition(
        key=ANNOUNCEMENTS,
        name={"uk": "Оголошення", "en": "Announcements"},
        description={"uk": "Важливі повідомлення від адміністрації", "en": "Important messages from the administrators"},
    ),
    TopicDefinition(
        key=SCHEDULE_CHANGES,
        name={"uk": "Зміни графіка", "en": "Schedule changes"},
        description={"uk": "Графік відключень оновлено або опубліковано на завтра", "en": "The outage schedule was updated or published for tomorrow"},
    ),
    TopicDefinition(
        key=OUTAGE_UPCOMING,
        name={"uk": "Нагадування про відключення", "en": "Outage reminders"},
        description={"uk": "Перед початком відключення за графіком", "en": "Before a scheduled outage starts"},
    ),
    TopicDefinition(
        key=EMERGENCY,
        name={"uk": "Аварійні відключення", "en": "Emergency outages"},
        description={"uk": "Коли діють аварійні відключення", "en": "When emergency outages are in effect"},
    ),
    TopicDefinition(
        key=POWER_STATUS,
        name={"uk": "Світло в будинках", "en": "Power in buildings"},
        description={"uk": "Світло зникло або з’явилося", "en": "Power went out or came back"},
    ),
    TopicDefinition(
        key=BATTERY_LOW,
        name={"uk": "Низький заряд батареї", "en": "Low battery"},
        description={"uk": "Батарея станції майже розряджена", "en": "The station battery is almost empty"},
    ),
]
