import logging
from beanie import PydanticObjectId
from fastapi import Body, FastAPI, Depends, HTTPException, Path, status
from fastapi_injector import Injected
from app.models.api import GridPowerRequest, ExtDataCreateRequest, ExtDataListRequest
from app.services import ExtDataService
from app.utils.jwt_dependencies import jwt_reporter_only, jwt_required


logger = logging.getLogger(__name__)


def register(app: FastAPI):

    @app.post("/api/ext-data/list")
    async def get_ext_data_list(
        body: ExtDataListRequest,
        _ = Depends(jwt_required),
        ext_data_service = Injected(ExtDataService),
    ):
        return await ext_data_service.get_ext_data(body)

    @app.post("/api/ext-data/grid-power")
    async def update_grid_power(
        body: GridPowerRequest,
        claims = Depends(jwt_reporter_only),
        ext_data_service = Injected(ExtDataService),
    ):
        grid_state = body.grid_power.state
        user_name = claims["sub"]

        try:
            data_id = await ext_data_service.add_ext_data(
                user_name = user_name,
                grid_state = grid_state
            )
            if data_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update data state"
                )

            return {"status": "ok"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating grid power: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    @app.post("/api/ext-data/create", status_code=status.HTTP_201_CREATED)
    async def create_ext_data(
        body: ExtDataCreateRequest = Body(...),
        _ = Depends(jwt_required),
        ext_data_service = Injected(ExtDataService),
    ):
        try:
            data_id = await ext_data_service.add_ext_data_by_user_id(
                user_id    = body.user_id,
                grid_state = body.grid_state,
                date       = body.received_at,
            )

            if data_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create ext_data",
                )

            return { "status": "ok", "id": data_id }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating ext data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @app.delete("/api/ext-data/delete/{data_id}")
    async def delete_ext_data(
        data_id: PydanticObjectId = Path(...),
        _ = Depends(jwt_required),
        ext_data_service = Injected(ExtDataService),
    ):
        try:
            success = await ext_data_service.delete_ext_data(data_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ext_data not found or failed to delete",
                )


            return {"status": "ok"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting ext data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    @app.get("/api/ext-data/{data_id}")
    async def get_ext_data_by_id(
        data_id: PydanticObjectId = Path(...),
        _ = Depends(jwt_required),
        ext_data_service = Injected(ExtDataService),
    ):
        try:
            data = await ext_data_service.get_by_id(data_id)

            if not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ext_data not found",
                )

            result = {
                "id": data.id,
                "user": data.user.name if data.user else None,
                "user_id": data.user_id,
                "grid_state": data.grid_state,
                "received_at": data.received_at.isoformat() if data.received_at else None,
            }

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting ext data by id: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
