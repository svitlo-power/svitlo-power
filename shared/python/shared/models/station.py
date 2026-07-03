from datetime import datetime
from typing import List, Optional
from beanie import Document
from pydantic import Field

from .beanie_filter import BeanieFilter
from .lookup import LookupModel, LookupValue


class Station(Document, LookupModel):
    station_id: Optional[int]
    station_name: Optional[str] = Field(None, max_length=128)

    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_address: Optional[str] = Field(None, max_length=64)

    region_nation_id: Optional[int] = None
    region_timezone: Optional[str] = Field(None, max_length=64)

    grid_interconnection_type: Optional[str] = Field(None, max_length=64)
    installed_capacity: Optional[float] = None

    start_operating_time: Optional[datetime] = None
    created_date: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    connection_status: Optional[str] = Field(None, max_length=64)
    contact_phone: Optional[str] = Field(None, max_length=64)
    owner_name: Optional[str] = Field(None, max_length=256)

    generation_power: Optional[float] = None
    battery_capacity: Optional[float] = None

    order: int = 1
    enabled: bool = True

    class Settings:
        name = "stations"

    def __str__(self):
        return (
            f"ClassName(id={self.id}, station_id='{self.station_id}', name='{self.station_name}', "
            f"connection_status='{self.connection_status}', contact_phone='{self.contact_phone}', "
            f"created_date={self.created_date}, grid_interconnection_type='{self.grid_interconnection_type}', "
            f"installed_capacity={self.installed_capacity}, location_address='{self.location_address}', "
            f"location_lat={self.location_lat}, location_lng={self.location_lng}, "
            f"owner_name='{self.owner_name}', region_nation_id={self.region_nation_id}, "
            f"region_timezone='{self.region_timezone}', generationPower={self.generation_power}, "
            f"lastUpdateTime={self.last_update_time}, start_operating_time={self.start_operating_time}, "
            f"battery_capacity={self.battery_capacity}, order={self.order}, enabled={self.enabled})"
        )

    def to_dict(self):
        return {
            "id": str(self.id),
            "station_id": self.station_id,
            "station_name": self.station_name,
            "location_lat": self.location_lat,
            "location_lng": self.location_lng,
            "location_address": self.location_address,
            "region_nation_id": self.region_nation_id,
            "region_timezone": self.region_timezone,
            "grid_interconnection_type": self.grid_interconnection_type,
            "installed_capacity": self.installed_capacity,
            "start_operating_time": self.start_operating_time,
            "created_date": self.created_date,
            "last_update_time": self.last_update_time,
            "connection_status": self.connection_status,
            "contact_phone": self.contact_phone,
            "owner_name": self.owner_name,
            "generation_power": self.generation_power,
            "battery_capacity": self.battery_capacity,
            "order": self.order,
            "enabled": self.enabled,
        }

    @classmethod
    async def get_lookup_values(self, filter: BeanieFilter) -> List[LookupValue]:
        stations = await self.find(filter).sort(Station.order).to_list()
        return [LookupValue(
            text  = s.station_name,
            value = s.id
        ) for s in stations]
