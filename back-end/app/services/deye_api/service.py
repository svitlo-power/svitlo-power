import logging
from aiohttp import ClientSession

from shared.services.deye_api import BaseDeyeClient, DeyeCredentials
from app.models.deye import DeyeStationList, DeyeStationData
from .models import DeyeConfig


logger = logging.getLogger(__name__)


class DeyeApiService:
    def __init__(self, config: DeyeConfig, session: ClientSession | None = None):
        creds = DeyeCredentials(
            base_url   = config.base_url,
            app_id     = config.app_id,
            app_secret = config.app_secret,
            email      = config.email,
            password   = config.password,
        )
        self._client = BaseDeyeClient(creds, session)

    async def init(self):
        await self._client.init()

    async def shutdown(self):
        await self._client.shutdown()

    async def refresh_token(self):
        await self._client.refresh_token()

    async def get_station_list(self) -> DeyeStationList | None:
        data = await self._client.get_station_list()
        if data is None or not data.get("success", False):
            logger.error(f"API error: {data.get('msg') if data else 'No data'}")
            return None
        return DeyeStationList.model_validate(data)

    async def get_station_data(self, station_id: int) -> DeyeStationData | None:
        data = await self._client.get_station_data(station_id)
        if data is None or not data.get("success", False):
            logger.error(f"API error: {data.get('msg') if data else 'No data'}")
            return None
        return DeyeStationData.model_validate(data)
