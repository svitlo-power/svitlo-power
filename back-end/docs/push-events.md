# Event-driven push notifications

Only `back-end` sends pushes; `app-back-end` handles device registration only.
Topics are app-level and filtered in MongoDB. They are not FCM topics.

## Flow

```
event source → trigger → PushEventDispatcher.dispatch(PushEvent)
  1. insert push_deliveries {dedup_key} (unique index)   → duplicate: log, stop
  2. PushTopic disabled                                   → status skipped_topic_disabled
  3. PushTemplate disabled                                → status skipped_template_disabled
  4. template "Send condition" renders False              → status skipped_condition
  5. recipients: enabled and topic ∉ disabled_topics      → none: status no_recipients
  6. group by PushDevice.language (unsupported → DEFAULT_LANGUAGE)
  7. render the Jinja2 template per language, one multicast per language
     via PushService.send_to_tokens (removes unregistered tokens)
  8. update the delivery record: sent / failed, counts
```

`PushDevice.buildings` is ignored. Every recipient gets every event; ⚡ and 🪫 name the building in the text.

## Triggers

| Topic | Event (source) | Dedup key | Recipients |
|---|---|---|---|
| `announcements` | Admin publishes an announcement (`POST /api/announcements`, Announcements page) | `announcement:{id}` | All devices |
| `schedule_changes` | `update_outages_schedule` job: the today/tomorrow schedule of `DashboardConfig.outages_schedule_queue` changed, or a day moved from `WaitingForSchedule` to a published state | `schedule:{queue}:{date}:{hash(slots)}` | All devices |
| `outage_upcoming` | `push_outage_upcoming` job (every 60 s): an outage of a `ScheduleApplies` day starts within `lead_minutes` | `upcoming:{queue}:{date}:{start_minutes}` | All devices |
| `emergency` | `update_outages_schedule` job: the day status changed to or from `EmergencyShutdowns` | `emergency:{queue}:{date}:{status}` | All devices |
| `power_status` | `push_power_status` job (every 15 s): a building's power state (as on the dashboard) changed and held for `debounce_seconds` | `power:{building_id}:{on\|off}:{changed_at}` | All devices, building name in the text |
| `battery_low` | `push_battery_low` job (every 60 s): station `battery_soc <= threshold`; re-arms above `threshold + hysteresis` | `battery:{station_id}:{low_episode_start}` | All devices, building name in the text |

### Notes

- **Schedule.** `OutagesScheduleService.update` compares the new schedule with the stored one (ignoring `updatedOn`) and sends SSE `outages_updated` only when it changed. The first fetch with nothing stored is a baseline and sends nothing. Adjacent slots (08:00–10:00, 10:00–12:00) are one outage.
- **Outage upcoming.** One reminder per outage; a moved outage gets a new key; an outage already in progress gets no reminder; an outage continuing over midnight is not reminded again at 00:00.
- **Power status.** The building has power while any of its report users reports it. A ping device that stops pinging for 120 s reports the power as off (`ExtDeviceService.check_pings`), and that counts as a power loss: the device is powered from the grid. The first observation of a building is a baseline. A flap shorter than the debounce time sends nothing.
- **Battery low.** Stations that are disabled, `ALL_OFFLINE` or assumed offline (stale data) are skipped, as are stations not linked to a building. A station linked to several buildings is notified once, for the first building.

## Templates (constructor)

Every topic has one `PushTemplate` (`push_templates`), edited on the Push page → **Event templates**:

- `title` / `body` — Jinja2 per language (`uk`, `en`); an empty language falls back to `DEFAULT_LANGUAGE`.
- `route` — Jinja2 app path put into `data.route`.
- `should_send` — optional Jinja2 condition; the event is skipped unless it renders `True`.
- `macros` — Jinja2 macros available in all fields.
- `params` — trigger parameters; defaults come from the settings below.

Defaults live in `app/services/push/events.py` and are created on start. Variables per event are shown in the editor (sample values); every template also gets `lang`, `topic` and `now`. Localizable values (building and station names, announcement texts) are resolved to the device language before rendering.

FCM `data` always has `topic`, plus `route` when it renders non-empty, and `buildingId` / `stationId` for ⚡ / 🪫.

## Settings

| Setting | Default | Template parameter |
|---|---|---|
| `PUSH_OUTAGE_LEAD_MINUTES` | 30 | `outage_upcoming.lead_minutes` |
| `PUSH_POWER_DEBOUNCE_SECONDS` | 60 | `power_status.debounce_seconds` |
| `PUSH_BATTERY_LOW_THRESHOLD` | 20 | `battery_low.threshold` |
| `PUSH_BATTERY_HYSTERESIS` | 10 | `battery_low.hysteresis` |
| `OUTAGES_REGION` / `OUTAGES_DSO` | 25 / 902 | YASNO ids used by `update_outages_schedule` |

## Delivery log

`push_deliveries` keeps one record per event for 30 days (TTL index): `dedup_key`, `topic`, `summary`, `building_id`, `status`, `recipients`, `recipients_by_language`, `success_count`, `failure_count`, `invalid_removed`, `created_at`, `error`. Admins see it on the Push page → **Delivery log** (`GET /api/push/deliveries`).

Logs and records never contain device tokens, credentials or full FCM responses; FCM failures are logged with the error code only.
