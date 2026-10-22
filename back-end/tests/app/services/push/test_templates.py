"""Tests for app/services/push/templates.py."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.api import PushTemplateRequest
from app.services.push.events import EVENT_DEFINITIONS, EVENTS_BY_TOPIC, LEAD_MINUTES
from app.services.push.templates import PushTemplateError, PushTemplatesService, localize, normalize_language
from app.services.push.topics import DEFAULT_TOPICS, OUTAGE_UPCOMING, POWER_STATUS
from shared.models.localizable_value import LocalizableValue
from shared.models.push_template import PushTemplate


def _settings(**kwargs):
    settings = MagicMock()
    settings.BOT_TIMEZONE = "Europe/Kyiv"
    settings.PUSH_OUTAGE_LEAD_MINUTES = 30
    settings.PUSH_POWER_DEBOUNCE_SECONDS = 60
    settings.PUSH_BATTERY_LOW_THRESHOLD = 20
    settings.PUSH_BATTERY_HYSTERESIS = 10
    for key, value in kwargs.items():
        setattr(settings, key, value)
    return settings


def _repo(templates=None):
    templates = templates or []
    repo = MagicMock()
    repo.get_all_templates = AsyncMock(return_value=templates)
    repo.get_template = AsyncMock(side_effect=lambda topic: next((t for t in templates if t.topic == topic), None))
    repo.add_template = AsyncMock(side_effect=lambda t: t)
    repo.save_template = AsyncMock(side_effect=lambda t: t)
    return repo


def _template(topic=POWER_STATUS, title=None, body=None, **kwargs) -> PushTemplate:
    return PushTemplate(
        topic=topic,
        title=LocalizableValue(title or {"uk": "Т {{ building.name }}", "en": "T {{ building.name }}"}),
        body=LocalizableValue(body or {"uk": "Б", "en": "B"}),
        **kwargs,
    )


def _request(**kwargs) -> PushTemplateRequest:
    values = {"title": {"uk": "Т", "en": "T"}, "body": {"uk": "Б", "en": "B"}}
    values.update(kwargs)
    return PushTemplateRequest(**values)


class TestDefinitions:
    def test_every_topic_has_an_event(self):
        assert { t.key for t in DEFAULT_TOPICS } == set(EVENTS_BY_TOPIC)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("definition", EVENT_DEFINITIONS, ids=lambda d: d.topic)
    async def test_default_templates_render_with_sample(self, definition):
        service = PushTemplatesService(_repo(), _settings())
        template = await service.get_template(definition.topic)

        for language in ("uk", "en"):
            rendered = await service.render(template, definition.sample(), language)
            assert rendered.title
            assert rendered.body
            assert "{" not in rendered.title + rendered.body


class TestLocalization:
    def test_normalize_language_falls_back_to_default(self):
        assert normalize_language("uk") == "uk"
        assert normalize_language("de") == "en"
        assert normalize_language(None) == "en"

    def test_localize_resolves_nested_values(self):
        value = {
            "building": {"id": "1", "name": {"uk": "Будинок", "en": "Building"}},
            "items": [LocalizableValue({"uk": "а", "en": "a"})],
        }
        assert localize(value, "uk") == {"building": {"id": "1", "name": "Будинок"}, "items": ["а"]}

    def test_localize_falls_back_to_default_language(self):
        assert localize({"name": {"en": "Building"}}, "uk") == {"name": "Building"}

    @pytest.mark.asyncio
    async def test_render_uses_device_language(self):
        service = PushTemplatesService(_repo(), _settings())
        variables = {"building": {"id": "1", "name": {"uk": "Будинок", "en": "Building"}}}

        uk = await service.render(_template(), variables, "uk")
        en = await service.render(_template(), variables, "en")

        assert uk.title == "Т Будинок"
        assert en.title == "T Building"

    @pytest.mark.asyncio
    async def test_render_falls_back_to_default_language_template(self):
        service = PushTemplatesService(_repo(), _settings())
        template = _template(title={"en": "Only english"}, body={"en": "B", "uk": ""})

        rendered = await service.render(template, {}, "uk")

        assert rendered.title == "Only english"
        assert rendered.body == "B"

    @pytest.mark.asyncio
    async def test_render_route_and_common_variables(self):
        service = PushTemplatesService(_repo(), _settings())
        template = _template(
            title={"en": "{{ lang }} {{ topic }}"},
            route="/buildings/{{ building.id }}",
        )

        rendered = await service.render(template, {"building": {"id": "42"}}, "en")

        assert rendered.title == "en power_status"
        assert rendered.route == "/buildings/42"

    @pytest.mark.asyncio
    async def test_render_error_names_the_field(self):
        service = PushTemplatesService(_repo(), _settings())
        template = _template(title={"en": "ok"}, body={"en": "{{ missing.value }}"})

        with pytest.raises(Exception, match="Body"):
            await service.render(template, {}, "en")


class TestShouldSend:
    @pytest.mark.asyncio
    async def test_empty_condition_sends(self):
        service = PushTemplatesService(_repo(), _settings())
        assert await service.should_send(_template(), {}) is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("available, expected", [(True, False), (False, True)])
    async def test_condition_uses_event_variables(self, available, expected):
        service = PushTemplatesService(_repo(), _settings())
        template = _template(should_send="{{ not available }}")

        assert await service.should_send(template, {"available": available}) is expected


class TestTemplatesStorage:
    @pytest.mark.asyncio
    async def test_ensure_default_templates_creates_only_missing(self):
        repo = _repo([_template(topic=POWER_STATUS)])
        service = PushTemplatesService(repo, _settings())

        await service.ensure_default_templates()

        created = { c.args[0].topic for c in repo.add_template.call_args_list }
        assert created == set(EVENTS_BY_TOPIC) - {POWER_STATUS}

    @pytest.mark.asyncio
    async def test_default_params_come_from_settings(self):
        service = PushTemplatesService(_repo(), _settings(PUSH_OUTAGE_LEAD_MINUTES=45))

        assert await service.get_param_value(OUTAGE_UPCOMING, LEAD_MINUTES) == 45

    @pytest.mark.asyncio
    async def test_stored_param_overrides_settings(self):
        stored = _template(topic=OUTAGE_UPCOMING, params={LEAD_MINUTES: 15})
        service = PushTemplatesService(_repo([stored]), _settings())

        assert await service.get_param_value(OUTAGE_UPCOMING, LEAD_MINUTES) == 15

    @pytest.mark.asyncio
    async def test_save_template_updates_fields(self):
        repo = _repo([_template(topic=OUTAGE_UPCOMING)])
        service = PushTemplatesService(repo, _settings())

        result = await service.save_template(OUTAGE_UPCOMING, _request(
            enabled=False, route="/schedule", shouldSend="{{ true }}", params={LEAD_MINUTES: 10},
        ))

        saved = repo.save_template.call_args.args[0]
        assert saved.enabled is False
        assert saved.should_send == "{{ true }}"
        assert saved.params == {LEAD_MINUTES: 10}
        assert result.params[0].value == 10
        assert result.params[0].default == 30

    @pytest.mark.asyncio
    async def test_save_unknown_topic_returns_none(self):
        service = PushTemplatesService(_repo(), _settings())
        assert await service.save_template("unknown", _request()) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("request_kwargs, message", [
        ({"title": {"en": "{% if %}"}}, "Syntax error in title"),
        ({"route": "{{ building.id"}, "Syntax error in route"),
        ({"title": {"en": "  "}}, "'title' must be filled"),
        ({"params": {"unknown": 1}}, "Unknown parameter"),
        ({"params": {LEAD_MINUTES: 0}}, "must be between"),
    ])
    async def test_save_rejects_invalid_template(self, request_kwargs, message):
        repo = _repo()
        service = PushTemplatesService(repo, _settings())

        with pytest.raises(PushTemplateError, match=message):
            await service.save_template(OUTAGE_UPCOMING, _request(**request_kwargs))
        repo.save_template.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_template_keeps_document_id(self):
        stored = _template(topic=POWER_STATUS, enabled=False)
        stored.id = "6650f0c2a1b2c3d4e5f60718"
        repo = _repo([stored])
        service = PushTemplatesService(repo, _settings())

        await service.reset_template(POWER_STATUS)

        saved = repo.save_template.call_args.args[0]
        assert str(saved.id) == "6650f0c2a1b2c3d4e5f60718"
        assert saved.enabled is True
        assert saved.title.root == EVENTS_BY_TOPIC[POWER_STATUS].title


class TestPreview:
    @pytest.mark.asyncio
    async def test_preview_renders_every_language(self):
        service = PushTemplatesService(_repo(), _settings())
        request = _request(title={"uk": "Т {{ building.name }}", "en": "T {{ building.name }}"})

        preview = await service.preview(POWER_STATUS, request)

        items = { i.language: i for i in preview.items }
        assert items["uk"].title == "Т Будинок 1"
        assert items["en"].title == "T Building 1"
        assert preview.should_send is True

    @pytest.mark.asyncio
    async def test_preview_reports_errors_instead_of_raising(self):
        service = PushTemplatesService(_repo(), _settings())
        request = _request(body={"en": "{{ 1 / 0 }}"}, shouldSend="{{ missing.x }}")

        preview = await service.preview(POWER_STATUS, request)

        assert all(i.error and "Body" in i.error for i in preview.items)
        assert preview.should_send_error

    @pytest.mark.asyncio
    async def test_render_sample_builds_message(self):
        service = PushTemplatesService(_repo(), _settings())
        request = _request(title={"en": "{{ building.name }}"}, route="/buildings/{{ building.id }}")

        message = await service.render_sample(POWER_STATUS, request, "de")

        assert message.title == "Building 1"
        assert message.data == {"topic": POWER_STATUS, "route": "/buildings/6650f0c2a1b2c3d4e5f60718"}


def test_sample_dates_are_real_dates():
    # Templates call strftime on these, so the samples must not be strings
    sample = EVENTS_BY_TOPIC[POWER_STATUS].sample()
    assert isinstance(sample["changed_at"], datetime)
