import logging
from beanie import PydanticObjectId
from injector import inject

from shared.language import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from shared.models.announcement import Announcement
from shared.models.localizable_value import LocalizableValue
from app.models.api import AnnouncementRequest, AnnouncementResponse, PushDeliveryResponse
from app.repositories import IAnnouncementsRepository, IPushDeliveriesRepository
from .dispatcher import PushEventDispatcher
from .events import PushEvent
from .templates import PushTemplateError
from .topics import ANNOUNCEMENTS


logger = logging.getLogger(__name__)


def _dedup_key(announcement_id: PydanticObjectId) -> str:
    return f"announcement:{announcement_id}"


def _clean(values: dict[str, str], field: str) -> dict[str, str]:
    values = { k: v.strip() for k, v in values.items() if v and v.strip() }
    if not values:
        raise PushTemplateError(f"'{field}' must be filled for at least one language")
    for language in values:
        if language not in SUPPORTED_LANGUAGES:
            raise PushTemplateError(f"Unsupported language '{language}'")
    return values


@inject
class AnnouncementsService:
    def __init__(
        self,
        announcements: IAnnouncementsRepository,
        deliveries: IPushDeliveriesRepository,
        dispatcher: PushEventDispatcher,
    ):
        self._announcements = announcements
        self._deliveries = deliveries
        self._dispatcher = dispatcher


    async def get_all(self) -> list[AnnouncementResponse]:
        announcements = await self._announcements.get_all()
        deliveries = {
            d.dedup_key: d
            for d in await self._deliveries.get_by_keys([_dedup_key(a.id) for a in announcements])
        }
        return [self._to_response(a, deliveries.get(_dedup_key(a.id))) for a in announcements]


    async def publish(self, request: AnnouncementRequest) -> AnnouncementResponse:
        """Saves the announcement and sends it to every subscriber in the background."""
        announcement = await self._announcements.add(Announcement(
            title   = LocalizableValue(_clean(request.title, "title")),
            body    = LocalizableValue(_clean(request.body, "body")),
        ))
        logger.info(f"Announcement {announcement.id} published")

        self._dispatcher.fire(PushEvent(
            topic       = ANNOUNCEMENTS,
            dedup_key   = _dedup_key(announcement.id),
            context     = {
                "announcement": {
                    "id": str(announcement.id),
                    "title": announcement.title,
                    "body": announcement.body,
                },
            },
            summary     = { "title": announcement.title.root.get(DEFAULT_LANGUAGE) or next(iter(announcement.title.root.values())) },
        ))
        return self._to_response(announcement, None)


    async def delete(self, announcement_id: PydanticObjectId) -> bool:
        return await self._announcements.delete(announcement_id)


    @staticmethod
    def _to_response(announcement: Announcement, delivery) -> AnnouncementResponse:
        return AnnouncementResponse(
            id          = announcement.id,
            title       = announcement.title.root,
            body        = announcement.body.root,
            created_at  = announcement.created_at,
            delivery    = PushDeliveryResponse.model_validate(delivery) if delivery else None,
        )
