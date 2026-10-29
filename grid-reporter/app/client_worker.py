import asyncio
import logging

from aiohttp import ClientSession

from shared.services.deye_api import BaseDeyeClient

from .config import ClientConfig
from .service import send_ext_data
from .settings import Settings
from .state_store import StateStore
from .transformers import is_grid_state_changed, normalize_station_data


class ClientWorker:

    def __init__(
        self,
        client: ClientConfig,
        deye_client: BaseDeyeClient,
        session: ClientSession,
        state_store: StateStore,
        settings: Settings,
    ):
        self.client = client
        self.deye_client = deye_client
        self.session = session
        self.state_store = state_store
        self.settings = settings

    async def poll_and_sync(self) -> None:
        prev_state = self.state_store.load(self.client.client_id)
        raw = await self.deye_client.get_station_data(self.client.station_id)
        logging.info("DEYE raw for %s: %s", self.client.client_id, raw)

        if not raw or not raw.get("success", True):
            logging.warning("Deye data unavailable for %s", self.client.client_id)
            return

        current_state = normalize_station_data(self.client, raw)
        grid_state = current_state.get("grid_state")

        if grid_state is None:
            logging.warning("Grid state missing for %s", self.client.client_id)
            return

        if not is_grid_state_changed(prev_state, current_state):
            logging.info("Grid state unchanged for %s", self.client.client_id)
            return

        logging.info(
            "Grid state changed for %s: %s",
            self.client.client_id,
            "ON" if grid_state else "OFF",
        )

        payload = {"grid_power": {"state": bool(grid_state)}}
        sent = await send_ext_data(self.session, self.client, self.settings, payload)
        if sent:
            self.state_store.save(self.client.client_id, current_state)
