from typing import List
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi_injector import Injected
from app.services import UsersService
from app.utils.jwt_dependencies import jwt_required
from app.models.api import UserListResponseModel


def register(app: FastAPI):

    @app.post("/api/users/users")
    async def get_users(
        current_user=Depends(jwt_required),
        users=Injected(UsersService)
    ) -> List[UserListResponseModel]:
        users = await users.get_users(all=True)
        current_name = current_user["sub"] if isinstance(current_user, dict) else current_user

        result = [u for u in users if u.name != current_name]

        return result

    @app.put("/api/users/save")
    async def save_user(
        request: Request,
        _=Depends(jwt_required),
        users=Injected(UsersService)
    ):
        body = await request.json()

        id = body.get("id")
        name = body.get("name")
        is_active = body.get("isActive", True)
        is_reporter = body.get("isReporter", False)
        report_mode = body.get("reportMode", 'event')

        user_id, reset_token = await users.save_user(
            id, name, is_active, is_reporter, report_mode
        )

        return {
            "success": True,
            "id": user_id,
            "resetToken": reset_token,
        }

    @app.delete("/api/users/delete/{user_id}")
    async def delete_user(
        user_id: str,
        _=Depends(jwt_required),
        users = Injected(UsersService),
    ):
        success = await users.delete_user(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return { "success": True }

    @app.post("/api/users/generate-token/{user_id}")
    async def generate_token(
        user_id: str,
        _=Depends(jwt_required),
        users = Injected(UsersService),
    ):
        token = await users.create_reporter_token(user_id)

        if not token:
            raise HTTPException(status_code=500, detail="Failed to generate token")

        return { "success": True, "token": token }

    @app.delete("/api/users/delete-token/{user_id}")
    async def delete_token(
        user_id: str,
        _=Depends(jwt_required),
        users = Injected(UsersService),
    ):
        success = await users.delete_reporter_token(user_id)

        return { "success": success }
