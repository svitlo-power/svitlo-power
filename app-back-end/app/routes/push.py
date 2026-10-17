from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi_injector import Injected

from shared.services import PushDevicesService
from shared.models.api.push import (
    PushDeviceRegisterRequest,
    PushDeviceTokenRequest,
    PushDeviceSubscriptionsRequest,
    PushDeviceResponse,
    PushTopicResponse,
)


def register(app: FastAPI):
    # Anonymous app devices only; sending and admin endpoints live in back-end,
    # which reads the same devices from the shared database.

    @app.post("/api/push/devices")
    async def register_device(
        body: PushDeviceRegisterRequest,
        push=Injected(PushDevicesService),
    ) -> PushDeviceResponse:
        """Register or refresh a device token - Android endpoint"""
        return await push.register_device(body)

    @app.post("/api/push/devices/current")
    async def get_device(
        body: PushDeviceTokenRequest,
        push=Injected(PushDevicesService),
    ) -> PushDeviceResponse:
        """Device registration state - Android endpoint"""
        device = await push.get_device(body.token)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered")
        return device

    @app.post("/api/push/devices/subscriptions")
    async def update_subscriptions(
        body: PushDeviceSubscriptionsRequest,
        push=Injected(PushDevicesService),
    ) -> PushDeviceResponse:
        """Topic subscriptions of a device - Android endpoint"""
        device = await push.update_subscriptions(body)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered")
        return device

    @app.post("/api/push/devices/unregister")
    async def unregister_device(
        body: PushDeviceTokenRequest,
        push=Injected(PushDevicesService),
    ):
        """Remove a device token - Android endpoint"""
        await push.unregister_device(body.token)
        return {"success": True}

    @app.get("/api/push/topics")
    async def get_topics(
        push=Injected(PushDevicesService),
    ) -> List[PushTopicResponse]:
        """Active push topics - Android endpoint"""
        return await push.get_enabled_topics()
