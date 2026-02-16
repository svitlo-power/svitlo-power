import logging
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_injector import Injected

from app.models.api import DevicePingRequest
from app.utils.jwt_dependencies import jwt_reporter_only
from app.services import IExtDeviceService
from app.models.api import ExtDeviceResponse


logger = logging.getLogger(__name__)


def register(app: FastAPI):

    @app.get("/api/ext-device", response_model=list[ExtDeviceResponse])
    async def get_devices(
        ext_device_service = Injected(IExtDeviceService),
    ):
        try:
            return await ext_device_service.get_all_devices()
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


    @app.post("/api/ext-device/ping")
    async def device_ping(
        body: DevicePingRequest,
        claims = Depends(jwt_reporter_only),
        ext_device_service = Injected(IExtDeviceService),
    ):
        user_name = claims["sub"]

        try:
            await ext_device_service.process_ping_request(body, user_name)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error receiving ping: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
