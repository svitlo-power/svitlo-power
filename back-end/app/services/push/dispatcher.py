import asyncio
import logging
from collections import defaultdict

from injector import inject

from shared.models.push_delivery import PushDelivery, PushDeliveryStatus
from app.repositories import IPushDeliveriesRepository, IPushDevicesRepository, IPushTopicsRepository
from app.models.api import PushDeliveryResponse
from .events import PushEvent
from .fcm_sender import PushMessage
from .service import PushService
from .templates import PushTemplatesService, normalize_language


logger = logging.getLogger(__name__)


@inject
class PushEventDispatcher:
    """Turns application events into localized notifications for the topic's subscribers."""

    # Strong references to running sends; asyncio keeps only weak ones
    _tasks: set[asyncio.Task] = set()

    def __init__(
        self,
        push: PushService,
        templates: PushTemplatesService,
        topics: IPushTopicsRepository,
        devices: IPushDevicesRepository,
        deliveries: IPushDeliveriesRepository,
    ):
        self._push = push
        self._templates = templates
        self._topics = topics
        self._devices = devices
        self._deliveries = deliveries


    def fire(self, event: PushEvent) -> asyncio.Task:
        """Dispatches in the background so the caller (a request or a job) is not delayed or broken."""
        task = asyncio.create_task(self._dispatch_safe(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task


    async def _dispatch_safe(self, event: PushEvent):
        try:
            await self.dispatch(event)
        except Exception as e:
            logger.error(f"Push {event.topic} [{event.dedup_key}] failed: {e!r}")


    async def _finish(self, delivery: PushDelivery, status: PushDeliveryStatus, reason: str | None = None) -> PushDelivery:
        delivery.status = status
        if reason:
            logger.info(f"Push {delivery.topic} [{delivery.dedup_key}] skipped: {reason}")
        return await self._deliveries.save(delivery)


    async def dispatch(self, event: PushEvent) -> PushDelivery | None:
        """Sends the event once; returns None when it was already processed."""
        logger.info(f"Push trigger {event.topic} activated [{event.dedup_key}]")

        delivery = PushDelivery(
            dedup_key   = event.dedup_key,
            topic       = event.topic,
            summary     = event.summary,
            building_id = event.building_id,
        )
        if not await self._deliveries.try_insert(delivery):
            logger.info(f"Push {event.topic} [{event.dedup_key}] skipped: duplicate")
            return None

        try:
            return await self._send(event, delivery)
        except Exception as e:
            logger.error(f"Push {event.topic} [{event.dedup_key}] failed: {e!r}")
            delivery.error = str(e)
            return await self._finish(delivery, PushDeliveryStatus.Failed)


    async def _send(self, event: PushEvent, delivery: PushDelivery) -> PushDelivery:
        topic = await self._topics.get_topic(event.topic)
        if not topic or not topic.enabled:
            return await self._finish(delivery, PushDeliveryStatus.SkippedTopicDisabled, "topic_disabled")

        template = await self._templates.get_template(event.topic)
        if not template or not template.enabled:
            return await self._finish(delivery, PushDeliveryStatus.SkippedTemplateDisabled, "template_disabled")

        if not await self._templates.should_send(template, event.context):
            return await self._finish(delivery, PushDeliveryStatus.SkippedCondition, "condition")

        by_language: dict[str, list[str]] = defaultdict(list)
        for recipient in await self._devices.get_topic_recipients(event.topic):
            by_language[normalize_language(recipient.language)].append(recipient.token)

        delivery.recipients = sum(len(tokens) for tokens in by_language.values())
        delivery.recipients_by_language = { lang: len(tokens) for lang, tokens in by_language.items() }
        if not delivery.recipients:
            return await self._finish(delivery, PushDeliveryStatus.NoRecipients, "no_recipients")

        logger.info(f"Push {event.topic} [{event.dedup_key}] recipients: {delivery.recipients_by_language}")

        errors = []
        for language, tokens in by_language.items():
            try:
                rendered = await self._templates.render(template, event.context, language)
            except Exception as e:
                # A broken template for one language must not stop the others
                logger.error(f"Push {event.topic} [{event.dedup_key}] render failed for {language}: {e}")
                errors.append(f"{language}: {e}")
                delivery.failure_count += len(tokens)
                continue

            data = { **event.data, "topic": event.topic }
            if rendered.route:
                data["route"] = rendered.route
            result = await self._push.send_to_tokens(tokens, PushMessage(
                title   = rendered.title,
                body    = rendered.body,
                data    = data,
            ))
            delivery.success_count += result.success_count
            delivery.failure_count += result.failure_count
            delivery.invalid_removed += result.removed_count

        delivery.error = "; ".join(errors) or None
        status = PushDeliveryStatus.Sent if delivery.success_count else PushDeliveryStatus.Failed
        logger.info(
            f"Push {event.topic} [{event.dedup_key}] {status.value}: "
            f"success {delivery.success_count}, failure {delivery.failure_count}, "
            f"invalid removed {delivery.invalid_removed}"
        )
        return await self._finish(delivery, status)


    async def get_recent_deliveries(self, limit: int = 200) -> list[PushDeliveryResponse]:
        deliveries = await self._deliveries.get_recent(limit)
        return [PushDeliveryResponse.model_validate(d) for d in deliveries]
