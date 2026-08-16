import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from injector import Injector, inject

from shared.models import Message
from shared.models.station import Station
from .models import MessageGeneratorConfig
from .context import TemplateRequestContext
from app.utils import generate_message, get_send_timeout, get_should_send
from app.repositories import IMessagesRepository, IStationsDataRepository
from ..interfaces import IMessageGeneratorService, MessageItem
from .requests import (
    AssumedStateRequest,
    AverageMinutesRequest,
    AverageAllRequest,
    AverageRequest,
)
from .template_method import TemplateMethod, TemplateMethodMode


logger = logging.getLogger(__name__)

_METHOD_KEYS = frozenset({
    AverageRequest.name,
    AverageAllRequest.name,
    AverageMinutesRequest.name,
    AssumedStateRequest.name,
    'timedelta',
})

def _strip_methods(obj: Any) -> Any:
    """Recursively remove template method callables from data structures."""
    if isinstance(obj, dict):
        return {
            k: _strip_methods(v) for k, v in obj.items()
            if k not in _METHOD_KEYS
        }
    if isinstance(obj, list):
        return [_strip_methods(item) for item in obj]
    return obj


@inject
class MessageGeneratorService(IMessageGeneratorService):
    def _try_get_timezone(self, timezone: str):
        try:
            return ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            logger.warning(f'Cannot get timezone {timezone}, falling back to UTC')
            return ZoneInfo('UTC')

    def __init__(
        self,
        config: MessageGeneratorConfig,
        messages: IMessagesRepository,
        stations_data: IStationsDataRepository,
        injector: Injector,
    ):
        self._message_timezone = self._try_get_timezone(config.timezone)
        self._messages = messages
        self._stations_data = stations_data
        self._injector = injector

    async def _populate_stations_data(self, template_data, stations: List[Station], force, lang):
        message_station = None
        for station in stations:
            if not station.enabled and not force:
                continue

            data = await self._stations_data.get_station_data_tuple(station.station_id)

            station_name = station.station_alias.get_culture_value(lang) if station.station_alias else station.station_name

            station_data = {
                **(data.to_dict(self._message_timezone) if data is not None else {}),
                'name': station_name,
                'grid_interconnection_type': station.grid_interconnection_type,
                'connection_status': station.connection_status,
                'battery_capacity': station.battery_capacity
            }
            template_data['stations'].append(station_data)

            if len(stations) == 1:
                template_data['station'] = station_data
                message_station = station

        return message_station

    def _add_methods(
            self,
            template_data,
            last_sent_time,
            mode: TemplateMethodMode,
            context: TemplateRequestContext):

        for station_data in template_data['stations']:
            if 'current' in station_data:
                station_id = station_data['current']['station_id']
                station_data[AverageRequest.name] = TemplateMethod(
                    AverageRequest,
                    station_id=station_id,
                    start_date=last_sent_time,
                ).bind(context, mode)
                station_data[AverageAllRequest.name] = TemplateMethod(
                    AverageRequest,
                    station_id=station_id
                ).bind(context, mode)
                station_data[AverageMinutesRequest.name] = TemplateMethod(
                    AverageMinutesRequest,
                    station_id=station_id
                ).bind(context, mode)
                station_data[AssumedStateRequest.name] = TemplateMethod(
                    AssumedStateRequest,
                    station_id=station_id
                ).bind(context, mode)
        if 'station' in template_data and template_data['station'] is not None and 'current' in template_data['station']:
            station_id = template_data['station']['current']['station_id']
            template_data['station'][AverageRequest.name] = TemplateMethod(
                AverageRequest,
                station_id=station_id,
                start_date=last_sent_time,
            ).bind(context, mode)
            template_data['station'][AverageAllRequest.name] = TemplateMethod(
                AverageAllRequest,
                station_id=station_id
            ).bind(context, mode)
            template_data['station'][AverageMinutesRequest.name] = TemplateMethod(
                AverageMinutesRequest,
                station_id=station_id
            ).bind(context, mode)
            template_data['station'][AssumedStateRequest.name] = TemplateMethod(
                AssumedStateRequest,
                station_id=station_id
            ).bind(context, mode)


    async def generate_message(self, message: Message, force = False, include_data = False) -> MessageItem | None:
        template_data = {
            'stations': [],
            'now': datetime.now(self._message_timezone),
            'timedelta': timedelta,
            'last_sent_time': message.last_sent_time.replace(tzinfo=timezone.utc).astimezone(self._message_timezone) if message.last_sent_time else None,
        }

        stations = sorted(message.stations, key=lambda s: s.order)

        if not any(station.enabled for station in stations):
            logger.info(f"All stations for message '{message.name}' are disabled")
            return None

        message_station = await self._populate_stations_data(template_data, stations, force, message.language)
        if len(stations) == 1 and message_station is None:
            logger.info(f"The station for message '{message.name}' is disabled")
            return None

        context = TemplateRequestContext(collect_data=include_data)
        self._add_methods(template_data, message.last_sent_time, TemplateMethodMode.Collect, context)

        timeout = await get_send_timeout(message.timeout_template, template_data, message.template_macros)
        template_data['timeout'] = timeout
        should_send = await get_should_send(message.should_send_template, template_data, message.template_macros)
        next_send_time = (
            (message.last_sent_time or datetime.min) + timedelta(seconds=timeout)
        ).replace(tzinfo=timezone.utc)

        _ = await generate_message(message.message_template, template_data, message.template_macros)
        await context.resolve_requests(self._injector)
        self._add_methods(template_data, message.last_sent_time, TemplateMethodMode.Resolve, context)
        message_content = await generate_message(message.message_template, template_data, message.template_macros)

        data = None
        if include_data:
            data = {
                **template_data,
                'requests': context.collected_data,
            }
            data = _strip_methods(json.loads(json.dumps(data, default=str)))

        return MessageItem(
            message = message_content,
            should_send = should_send,
            timeout = timeout,
            next_send_time = datetime.now(timezone.utc) if next_send_time < datetime.now(timezone.utc) else next_send_time,
            data = data,
        )
