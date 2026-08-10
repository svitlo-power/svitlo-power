from beanie import PydanticObjectId
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi_injector import Injected
from pydantic import BaseModel, Field
from app.services.authorization import AuthorizationService
from app.utils import get_client_ip
from app.utils.jwt_dependencies import jwt_refresh_required, jwt_required

class LoginRequest(BaseModel):
    user_name: str = Field(alias="userName")
    password: str


class SaveProfileRequest(BaseModel):
    user_id: PydanticObjectId = Field(alias="userId")
    user_name: str = Field(alias="userName")


class StartPasswordChangeRequest(BaseModel):
    user_name: str = Field(alias="userName")


class CancelPasswordChangeRequest(BaseModel):
    user_name: str = Field(alias="userName")


class ChangePasswordRequest(BaseModel):
    reset_token: str = Field(alias="resetToken")
    new_password: str = Field(alias="newPassword")


def register(app: FastAPI):
    @app.post("/api/auth/login")
    async def login(
        request: Request,
        body: LoginRequest,
        authorization: AuthorizationService = Injected(AuthorizationService),
    ):
        try:
            ip_address = get_client_ip(request)
            access_token, refresh_token = await authorization.login(
                body.user_name, body.password, ip_address
            )
            return {
                "success": True,
                "accessToken": access_token,
                "refreshToken": refresh_token
            }
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    @app.get("/api/auth/profile")
    async def profile(
        claims=Depends(jwt_required),
        authorization: AuthorizationService = Injected(AuthorizationService),
    ):
        user_name = claims["sub"]
        user = await authorization.get_user(user_name)
        if user is None:
            raise HTTPException(status_code=400, detail="Cannot find user")

        return {"success": True, "userName": user.name, "userId": str(user.id)}

    @app.post("/api/auth/saveProfile")
    async def save_profile(
        body: SaveProfileRequest,
        _=Depends(jwt_required),
        authorization: AuthorizationService = Injected(AuthorizationService),
    ):
        await authorization.rename_user(body.user_id, body.user_name)
        return {"success": True }

    @app.post("/api/auth/startPasswordChange")
    async def start_password_change(
        body: StartPasswordChangeRequest,
        _=Depends(jwt_required),
        authorization: AuthorizationService = Injected(AuthorizationService)
    ):
        try:
            token = await authorization.start_change_password(body.user_name, hours=2.5)
            return {"success": True, "resetToken": token}
        except ValueError as e:
            raise HTTPException(status_code=500, detail="Error changing password")

    @app.post("/api/auth/cancelPasswordChange")
    async def cancel_password_change(
        body: CancelPasswordChangeRequest,
        _=Depends(jwt_required),
        authorization: AuthorizationService = Injected(AuthorizationService)
    ):
        try:
            await authorization.cancel_change_password(body.user_name)
            return {"success": True}
        except ValueError as e:
            raise HTTPException(status_code=500, detail="Error changing password")

    @app.post("/api/auth/changePassword")
    async def change_password(
        body: ChangePasswordRequest,
        authorization: AuthorizationService = Injected(AuthorizationService)
    ):
        if not body.reset_token or not body.new_password:
            raise HTTPException(status_code=400, detail="Invalid request")
        try:
            await authorization.change_password(body.reset_token, body.new_password)
            return {"success": True}
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @app.post("/api/auth/refresh")
    async def refresh(
        claims=Depends(jwt_refresh_required),
        authorization: AuthorizationService = Injected(AuthorizationService)
    ):
        identity = claims["sub"]
        access_token = await authorization.refresh_token(identity)
        refresh_token = claims.get("refresh_token", None)
        return {"success": True, "accessToken": access_token, "refreshToken": refresh_token}
