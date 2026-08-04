from beanie import PydanticObjectId
from fastapi import FastAPI, Depends, HTTPException
from fastapi_injector import Injected
from typing import List

from app.models.api import (
    CreateDeyeConnectionRequest,
    UpdateDeyeConnectionRequest,
    DeyeConnectionResponse,
    DeyeConnectionDefaultsResponse,
)
from app.repositories import IStationsRepository
from app.services import DeyeConnectionsService
from app.settings import Settings
from app.utils.jwt_dependencies import jwt_required


def register(app: FastAPI):

    @app.get("/api/deye-connections", response_model=List[DeyeConnectionResponse])
    async def get_connections(
        _ = Depends(jwt_required),
        connections = Injected(DeyeConnectionsService),
    ):
        return connections.get_connections()


    @app.get("/api/deye-connections/defaults", response_model=DeyeConnectionDefaultsResponse)
    async def get_connection_defaults(
        _ = Depends(jwt_required),
        settings = Injected(Settings),
    ):
        return DeyeConnectionDefaultsResponse(base_url=settings.DEYE_BASE_URL)


    @app.post("/api/deye-connections")
    async def create_connection(
        body: CreateDeyeConnectionRequest,
        _ = Depends(jwt_required),
        connections = Injected(DeyeConnectionsService),
    ):
        connection = await connections.create_connection(
            name                  = body.name,
            base_url              = body.base_url,
            app_id                = body.app_id,
            app_secret            = body.app_secret,
            email                 = body.email,
            password              = body.password,
            sync_stations_on_poll = body.sync_stations_on_poll,
        )
        return { "success": True, "id": str(connection.id) }


    @app.put("/api/deye-connections/{connection_id}")
    async def update_connection(
        connection_id: PydanticObjectId,
        body: UpdateDeyeConnectionRequest,
        _ = Depends(jwt_required),
        connections = Injected(DeyeConnectionsService),
    ):
        try:
            await connections.update_connection(
                connection_id         = connection_id,
                name                  = body.name,
                base_url              = body.base_url,
                app_id                = body.app_id,
                email                 = body.email,
                sync_stations_on_poll = body.sync_stations_on_poll,
                app_secret            = body.app_secret or None,
                password              = body.password or None,
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="Connection not found")
        return { "success": True, "id": str(connection_id) }


    @app.delete("/api/deye-connections/{connection_id}")
    async def delete_connection(
        connection_id: PydanticObjectId,
        _ = Depends(jwt_required),
        connections = Injected(DeyeConnectionsService),
        stations = Injected(IStationsRepository),
    ):
        stations_count = await stations.count_by_connection(connection_id)
        if stations_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Connection is used by {stations_count} station(s)",
            )
        await connections.delete_connection(connection_id)
        return { "success": True, "id": str(connection_id) }
