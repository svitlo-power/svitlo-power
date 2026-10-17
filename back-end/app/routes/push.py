import logging
from typing import List
from beanie import PydanticObjectId
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_injector import Injected

from app.models.api import (
    PushDeviceRegisterRequest,
    PushDeviceTokenRequest,
    PushDeviceSubscriptionsRequest,
    PushDeviceResponse,
    PushTestRequest,
    PushSendResult,
    PushTopicResponse,
    PushTopicAdminResponse,
    PushTopicStateRequest,
)
from app.services import PushService, PushMessage
from app.utils.jwt_dependencies import jwt_required


logger = logging.getLogger(__name__)


def register(app: FastAPI):

    # -------------------------
    # Public (anonymous app devices)
    # -------------------------

    @app.post("/api/push/devices")
    async def register_device(
        body: PushDeviceRegisterRequest,
        push = Injected(PushService),
    ) -> PushDeviceResponse:
        return await push.register_device(body)


    @app.post("/api/push/devices/current")
    async def get_device(
        body: PushDeviceTokenRequest,
        push = Injected(PushService),
    ) -> PushDeviceResponse:
        device = await push.get_device(body.token)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered")
        return device


    @app.post("/api/push/devices/subscriptions")
    async def update_subscriptions(
        body: PushDeviceSubscriptionsRequest,
        push = Injected(PushService),
    ) -> PushDeviceResponse:
        device = await push.update_subscriptions(body)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered")
        return device


    @app.post("/api/push/devices/unregister")
    async def unregister_device(
        body: PushDeviceTokenRequest,
        push = Injected(PushService),
    ):
        await push.unregister_device(body.token)
        return { 'success': True }


    @app.get("/api/push/topics")
    async def get_topics(
        push = Injected(PushService),
    ) -> List[PushTopicResponse]:
        return await push.get_enabled_topics()


    # -------------------------
    # Admin
    # -------------------------

    @app.get("/api/push/topics/all")
    async def get_all_topics(
        _ = Depends(jwt_required),
        push = Injected(PushService),
    ) -> List[PushTopicAdminResponse]:
        return await push.get_all_topics()


    @app.patch("/api/push/topics/{key}/state")
    async def set_topic_state(
        key: str,
        body: PushTopicStateRequest,
        _ = Depends(jwt_required),
        push = Injected(PushService),
    ):
        if not await push.set_topic_state(key, body.enabled):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
        return { 'success': True, 'key': key }


    @app.get("/api/push/devices")
    async def get_devices(
        _ = Depends(jwt_required),
        push = Injected(PushService),
    ) -> List[PushDeviceResponse]:
        return await push.get_all_devices()


    @app.delete("/api/push/devices/{device_id}")
    async def delete_device(
        device_id: PydanticObjectId,
        _ = Depends(jwt_required),
        push = Injected(PushService),
    ):
        if not await push.delete_device(device_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return { 'success': True }


    @app.post("/api/push/test")
    async def send_test(
        body: PushTestRequest,
        _ = Depends(jwt_required),
        push = Injected(PushService),
    ) -> PushSendResult:
        data = { "route": body.route } if body.route else {}
        message = PushMessage(title=body.title, body=body.body, data=data)

        try:
            if body.topic:
                result = await push.send_to_topic(body.topic, message)
                if not result:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
                return result
            if body.device_id:
                result = await push.send_to_device(body.device_id, message)
                if not result:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
                return result
            return await push.send_to_all(message)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending test push: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
