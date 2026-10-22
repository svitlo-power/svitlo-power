import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from injector import inject
from jinja2 import Environment, TemplateSyntaxError

from shared.language import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from shared.models.localizable_value import LocalizableValue
from shared.models.push_template import PushTemplate
from app.models.api import (
    PushTemplateParamResponse,
    PushTemplatePreviewItem,
    PushTemplatePreviewResponse,
    PushTemplateRequest,
    PushTemplateResponse,
)
from app.repositories import IPushTemplatesRepository
from app.settings import Settings
from app.utils import get_should_send, render_template
from .events import EVENT_DEFINITIONS, EVENTS_BY_TOPIC, EventDefinition
from .fcm_sender import PushMessage


logger = logging.getLogger(__name__)


class PushTemplateError(ValueError):
    pass


@dataclass
class RenderedPush:
    title: str
    body: str
    route: str


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def _localized_text(values: dict[str, str], language: str) -> str:
    """Text for the language, falling back to the default language and then to any filled one."""
    return (
        values.get(language)
        or values.get(DEFAULT_LANGUAGE)
        or next((v for v in values.values() if v), "")
    )


def _is_localized(value: dict) -> bool:
    return bool(value) and all(k in SUPPORTED_LANGUAGES and isinstance(v, str) for k, v in value.items())


def localize(value: Any, language: str) -> Any:
    """Replaces LocalizableValue and {lang: text} values with the text for the language."""
    if isinstance(value, LocalizableValue):
        return _localized_text(value.root, language)
    if isinstance(value, dict):
        if _is_localized(value):
            return _localized_text(value, language)
        return { k: localize(v, language) for k, v in value.items() }
    if isinstance(value, list):
        return [localize(v, language) for v in value]
    return value


@inject
class PushTemplatesService:
    def __init__(self, templates: IPushTemplatesRepository, settings: Settings):
        self._templates = templates
        self._settings = settings
        try:
            self._timezone = ZoneInfo(settings.BOT_TIMEZONE)
        except ZoneInfoNotFoundError:
            logger.warning(f"Cannot get timezone {settings.BOT_TIMEZONE}, falling back to UTC")
            self._timezone = ZoneInfo("UTC")

    @property
    def timezone(self) -> ZoneInfo:
        return self._timezone

    def _default_params(self, definition: EventDefinition) -> dict[str, int]:
        return { p.key: p.default(self._settings) for p in definition.params }

    def _default_template(self, definition: EventDefinition) -> PushTemplate:
        return PushTemplate(
            topic   = definition.topic,
            title   = LocalizableValue(definition.title),
            body    = LocalizableValue(definition.body),
            route   = definition.route,
            params  = self._default_params(definition),
        )


    async def ensure_default_templates(self):
        """Creates missing templates of the built-in events; existing ones keep the admin's changes."""
        existing = { t.topic for t in await self._templates.get_all_templates() }
        for definition in EVENT_DEFINITIONS:
            if definition.topic in existing:
                continue
            await self._templates.add_template(self._default_template(definition))
            logger.info(f"Created push template {definition.topic}")


    async def get_template(self, topic: str) -> PushTemplate | None:
        """Stored template of the topic, or the built-in default when it was not created yet."""
        template = await self._templates.get_template(topic)
        if template:
            return template
        definition = EVENTS_BY_TOPIC.get(topic)
        return self._default_template(definition) if definition else None


    def get_param(self, template: PushTemplate, key: str) -> int:
        if key in template.params:
            return template.params[key]
        definition = EVENTS_BY_TOPIC[template.topic]
        return next(p.default(self._settings) for p in definition.params if p.key == key)


    async def get_param_value(self, topic: str, key: str) -> int:
        return self.get_param(await self.get_template(topic), key)


    def _to_response(self, template: PushTemplate) -> PushTemplateResponse:
        definition = EVENTS_BY_TOPIC[template.topic]
        return PushTemplateResponse(
            topic       = template.topic,
            enabled     = template.enabled,
            title       = template.title.root,
            body        = template.body.root,
            route       = template.route,
            should_send = template.should_send,
            macros      = template.macros,
            params      = [
                PushTemplateParamResponse(
                    key     = p.key,
                    value   = self.get_param(template, p.key),
                    default = p.default(self._settings),
                    min     = p.min,
                    max     = p.max,
                )
                for p in definition.params
            ],
            variables   = definition.sample(),
            updated_at  = template.updated_at,
        )


    async def get_all_templates(self) -> list[PushTemplateResponse]:
        return [
            self._to_response(await self.get_template(d.topic))
            for d in EVENT_DEFINITIONS
        ]


    async def get_template_response(self, topic: str) -> PushTemplateResponse | None:
        if topic not in EVENTS_BY_TOPIC:
            return None
        return self._to_response(await self.get_template(topic))


    def _validate(self, definition: EventDefinition, request: PushTemplateRequest):
        for values, field in ((request.title, "title"), (request.body, "body")):
            if not any(v.strip() for v in values.values()):
                raise PushTemplateError(f"'{field}' must be filled for at least one language")
            for language in values:
                if language not in SUPPORTED_LANGUAGES:
                    raise PushTemplateError(f"Unsupported language '{language}'")

        sources = [
            *(("title", lang, text) for lang, text in request.title.items()),
            *(("body", lang, text) for lang, text in request.body.items()),
            ("route", None, request.route),
            ("shouldSend", None, request.should_send),
            ("macros", None, request.macros),
        ]
        environment = Environment()
        for field, language, source in sources:
            if not source:
                continue
            try:
                environment.parse(source)
            except TemplateSyntaxError as e:
                where = f"{field} ({language})" if language else field
                raise PushTemplateError(f"Syntax error in {where}, line {e.lineno}: {e.message}")

        allowed = { p.key: p for p in definition.params }
        for key, value in request.params.items():
            param = allowed.get(key)
            if not param:
                raise PushTemplateError(f"Unknown parameter '{key}'")
            if not param.min <= value <= param.max:
                raise PushTemplateError(f"'{key}' must be between {param.min} and {param.max}")


    async def save_template(self, topic: str, request: PushTemplateRequest) -> PushTemplateResponse | None:
        definition = EVENTS_BY_TOPIC.get(topic)
        if not definition:
            return None
        self._validate(definition, request)

        template = await self._templates.get_template(topic) or self._default_template(definition)
        template.enabled = request.enabled
        template.title = LocalizableValue(request.title)
        template.body = LocalizableValue(request.body)
        template.route = request.route
        template.should_send = request.should_send or None
        template.macros = request.macros or None
        template.params = { **self._default_params(definition), **request.params }
        template.updated_at = datetime.now(timezone.utc)

        template = await self._templates.save_template(template)
        logger.info(f"Push template {topic} updated")
        return self._to_response(template)


    async def reset_template(self, topic: str) -> PushTemplateResponse | None:
        definition = EVENTS_BY_TOPIC.get(topic)
        if not definition:
            return None
        default = self._default_template(definition)
        template = await self._templates.get_template(topic)
        if template:
            default.id = template.id
        template = await self._templates.save_template(default)
        logger.info(f"Push template {topic} reset to default")
        return self._to_response(template)


    def build_context(self, template: PushTemplate, variables: dict[str, Any], language: str) -> dict[str, Any]:
        return {
            **localize(variables, language),
            "lang": language,
            "topic": template.topic,
            "now": datetime.now(self._timezone),
        }


    async def should_send(self, template: PushTemplate, variables: dict[str, Any]) -> bool:
        if not template.should_send:
            return True
        context = self.build_context(template, variables, DEFAULT_LANGUAGE)
        return await get_should_send(template.should_send, context, template.macros)


    async def render(self, template: PushTemplate, variables: dict[str, Any], language: str) -> RenderedPush:
        context = self.build_context(template, variables, language)
        title = await render_template(_localized_text(template.title.root, language), context, template.macros, "Title")
        body = await render_template(_localized_text(template.body.root, language), context, template.macros, "Body")
        route = await render_template(template.route, context, template.macros, "Route") if template.route else ""
        return RenderedPush(title=title.strip(), body=body.strip(), route=route.strip())


    @staticmethod
    def _from_request(topic: str, request: PushTemplateRequest) -> PushTemplate:
        """Unsaved template built from the editor state."""
        return PushTemplate(
            topic       = topic,
            enabled     = request.enabled,
            title       = LocalizableValue(request.title),
            body        = LocalizableValue(request.body),
            route       = request.route,
            should_send = request.should_send or None,
            macros      = request.macros or None,
            params      = request.params,
        )


    async def render_sample(self, topic: str, request: PushTemplateRequest, language: str) -> PushMessage | None:
        """The editor state rendered with the sample variables, for a test send."""
        definition = EVENTS_BY_TOPIC.get(topic)
        if not definition:
            return None
        rendered = await self.render(self._from_request(topic, request), definition.sample(), normalize_language(language))
        data = { "topic": topic }
        if rendered.route:
            data["route"] = rendered.route
        return PushMessage(title=rendered.title, body=rendered.body, data=data)


    async def preview(self, topic: str, request: PushTemplateRequest) -> PushTemplatePreviewResponse | None:
        definition = EVENTS_BY_TOPIC.get(topic)
        if not definition:
            return None

        template = self._from_request(topic, request)
        variables = definition.sample()

        response = PushTemplatePreviewResponse(items=[])
        try:
            response.should_send = await self.should_send(template, variables)
        except Exception as e:
            response.should_send_error = str(e)

        for language in sorted(SUPPORTED_LANGUAGES):
            try:
                rendered = await self.render(template, variables, language)
                response.items.append(PushTemplatePreviewItem(
                    language    = language,
                    title       = rendered.title,
                    body        = rendered.body,
                    route       = rendered.route,
                ))
            except Exception as e:
                response.items.append(PushTemplatePreviewItem(language=language, error=str(e)))

        return response
