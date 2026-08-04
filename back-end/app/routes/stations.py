from fastapi import FastAPI, Depends, Body
from fastapi_injector import Injected

from app.services import StationConnectionsService, StationsService
from app.utils.jwt_dependencies import jwt_required


def register(app: FastAPI):

    @app.post("/api/stations/stations")
    async def get_stations(
        _=Depends(jwt_required),
        stations=Injected(StationsService),
        connections=Injected(StationConnectionsService),
    ):
        stations = await stations.get_stations()
        connection_names = {c.id: c.name for c in connections.get_connections()}

        stations_dict = [
            {
                "id": str(station.id),
                "stationName": station.station_name,
                "connectionStatus": station.connection_status,
                "gridInterconnectionType": station.grid_interconnection_type,
                "lastUpdateTime": station.last_update_time,
                "batteryCapacity": station.battery_capacity or 0.0,
                "enabled": station.enabled,
                "order": station.order,
                "connectionName": connection_names.get(station.connection_id),
            }
            for station in stations
        ]

        return stations_dict

    @app.put("/api/stations/save")
    async def save_station(
        payload: dict = Body(...),
        _=Depends(jwt_required),
        stations=Injected(StationsService),
    ):
        station_id = payload.get("id")
        enabled = payload.get("enabled", False)
        order = payload.get("order", 1)
        battery_capacity = payload.get("batteryCapacity")

        await stations.edit_station(station_id, enabled, order, battery_capacity)

        return {"success": True, "id": station_id }
