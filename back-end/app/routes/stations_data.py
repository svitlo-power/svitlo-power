from datetime import timedelta, timezone
from statistics import mean
from fastapi import FastAPI, Depends, HTTPException, Body, Path
from fastapi_injector import Injected
from app.services import StationsService
from shared import current_language
from app.utils.jwt_dependencies import jwt_required
from app.models.api import StationsDataRequest

def register(app: FastAPI):

    @app.post("/api/stationsData/stationsData")
    async def get_stations_data(
        body: StationsDataRequest,
        _ = Depends(jwt_required),
        stations = Injected(StationsService)
    ):
        is_range_request = body.start_date is not None and body.end_date is not None
        stations_data = await (
            stations.get_stations_data_range(
                body.start_date,
                body.end_date,
            ) if is_range_request
            else stations.get_stations_data(body.last_seconds)
        )

        def downsample_data(data, max_records):
            if not max_records or len(data) <= max_records:
                return data

            result = [data[0]]
            n_segments = max_records - 2
            if n_segments <= 0:
                return [data[0], data[-1]]

            chunk_size = len(data) / n_segments
            start_time = data[0].last_update_time
            end_time = data[-1].last_update_time
            total_duration = (end_time - start_time).total_seconds()

            for i in range(n_segments):
                start_idx = int(i * chunk_size)
                end_idx = int((i + 1) * chunk_size)
                chunk = data[start_idx:end_idx]
                if not chunk:
                    continue

                avg_record = {
                    "battery_soc": mean(d.battery_soc or 0 for d in chunk),
                    "discharge_power": mean(d.discharge_power or 0 for d in chunk),
                    "charge_power": mean(abs(d.charge_power) if d.charge_power else 0 for d in chunk),
                    "consumption_power": mean(d.consumption_power or 0 for d in chunk),
                    "last_update_time": start_time + timedelta(seconds=((i + 1) * total_duration / (n_segments + 1)))
                }
                result.append(avg_record)

            result.append(data[-1])
            return result

        def get_station_data(station, station_data):
            station_data = downsample_data(station_data, body.records_count)
            return {
                "id": str(station.id),
                "name": station.station_alias.get_culture_value(current_language.get()) if station.station_alias else station.station_name,
                "data": [
                    {
                        "batterySoc": d["battery_soc"] if isinstance(d, dict) else d.battery_soc,
                        "dischargePower": d["discharge_power"] if isinstance(d, dict) else (d.discharge_power or 0),
                        "chargePower": d["charge_power"] if isinstance(d, dict) else (abs(d.charge_power) if d.charge_power else 0),
                        "consumptionPower": d["consumption_power"] if isinstance(d, dict) else (d.consumption_power or 0),
                        "date": (d["last_update_time"] if isinstance(d, dict) else d.last_update_time).replace(tzinfo=timezone.utc).isoformat()
                    }
                    for d in station_data
                ]
            }

        return [
            get_station_data(station, station_data)
            for (station, station_data) in stations_data
        ]


    @app.post("/api/stationsData/stationDetails/{station_id}")
    async def get_station_details(
        station_id: str = Path(..., description="Station ID"),
        payload: dict = Body(...),
        _ = Depends(jwt_required),
        stations = Injected(StationsService)
    ):
        last_seconds: int = payload.get("lastSeconds", 86400)  # Default 24h

        station, station_data = await stations.get_station_data(station_id, last_seconds)
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        data_list = [
            {
                "id": str(data.id),
                "stationId": data.station_id,
                "batteryPower": data.battery_power,
                "batterySoc": data.battery_soc,
                "chargePower": data.charge_power,
                "code": data.code,
                "consumptionPower": data.consumption_power,
                "dischargePower": data.discharge_power,
                "generationPower": data.generation_power,
                "gridPower": data.grid_power,
                "irradiateIntensity": data.irradiate_intensity,
                "lastUpdateTime": data.last_update_time,
                "msg": data.msg,
                "purchasePower": data.purchase_power,
                "requestId": data.request_id,
                "wirePower": data.wire_power,
            }
            for data in station_data
        ]

        return {
            "station": {
                "id": str(station.id),
                "stationId": station.station_id,
                "stationName": station.station_name,
                "connectionStatus": station.connection_status,
                "gridInterconnectionType": station.grid_interconnection_type,
                "installedCapacity": station.installed_capacity,
                "batteryCapacity": station.battery_capacity,
                "lastUpdateTime": station.last_update_time,
            },
            "data": data_list,
            "dataCount": len(data_list)
        }
