from typing import List
from beanie import PydanticObjectId
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_injector import Injected

from app.models.api import AnnouncementRequest, AnnouncementResponse
from app.services import AnnouncementsService, PushTemplateError
from app.utils.jwt_dependencies import jwt_required


def register(app: FastAPI):

    @app.get("/api/announcements")
    async def get_announcements(
        _ = Depends(jwt_required),
        announcements = Injected(AnnouncementsService),
    ) -> List[AnnouncementResponse]:
        return await announcements.get_all()


    @app.post("/api/announcements", status_code=status.HTTP_201_CREATED)
    async def publish_announcement(
        body: AnnouncementRequest,
        _ = Depends(jwt_required),
        announcements = Injected(AnnouncementsService),
    ) -> AnnouncementResponse:
        try:
            return await announcements.publish(body)
        except PushTemplateError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


    @app.delete("/api/announcements/{announcement_id}")
    async def delete_announcement(
        announcement_id: PydanticObjectId,
        _ = Depends(jwt_required),
        announcements = Injected(AnnouncementsService),
    ):
        if not await announcements.delete(announcement_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
        return { 'success': True }
