from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from injector import inject
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.settings import Settings
from shared.models import User
from app.repositories import IUsersRepository, ILoginHistoryRepository
from shared.services.translation.service import TranslationService
from shared.utils.jwt_utils import create_access_token, create_refresh_token
from shared.utils.key_generation import generate_password_reset_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

@inject
class AuthorizationService:
    def __init__(
        self,
        users_repository: IUsersRepository,
        login_history_repository: ILoginHistoryRepository,
        settings: Settings,
    ):
        self._settings: Settings = settings
        self._users_repository: IUsersRepository = users_repository
        self._login_history_repository: ILoginHistoryRepository = login_history_repository

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> str:
        credentials_error = HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = TranslationService.t("common.error.invalidToken"),
            headers     = {"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, self._settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_error

            return username
        except JWTError:
            raise credentials_error


    async def _get_user(self, user_name: str, password: str):
        user = await self._users_repository.get_user(user_name)
        if not user:
            raise ValueError(TranslationService.t("common.error.invalidLoginOrPassword"))
        if user.is_reporter:
            raise ValueError(TranslationService.t("common.error.invalidLoginOrPassword"))
        if not pwd_context.verify(password, user.password):
            raise ValueError(TranslationService.t("common.error.invalidLoginOrPassword"))
        return user

    async def login(self, user_name: str, password: str, ip_address: str = None):
        user = await self._get_user(user_name, password)

        await self._login_history_repository.add_login_history(
            user_id=user.id,
            ip_address=ip_address,
        )

        access = create_access_token(
            identity   = user.name,
            expires    = self._settings.JWT_ACCESS_TOKEN_EXPIRES,
            secret_key = self._settings.JWT_SECRET_KEY,
        )

        refresh = create_refresh_token(
            identity   = user.name,
            expires    = self._settings.JWT_REFRESH_TOKEN_EXPIRES,
            secret_key = self._settings.JWT_SECRET_KEY,
        )

        return access, refresh
    
    async def get_user(self, user_name: str) -> User:
        return await self._users_repository.get_user(user_name)

    async def refresh_token(self, user_name):
        user = await self._users_repository.get_user(user_name)
        if not user:
            raise ValueError(TranslationService.t("common.error.userNotFound"))
        if user.is_reporter:
            raise ValueError(TranslationService.t("common.error.userCannotLogIn"))

        return create_access_token(
            identity   = user.name,
            expires    = self._settings.JWT_ACCESS_TOKEN_EXPIRES,
            secret_key = self._settings.JWT_SECRET_KEY
        )

    async def _generate_passwd_reset_token(self, user: User, hours: int):
        password_reset_token, reset_token_expiration = generate_password_reset_token(hours)
        await self._users_repository.set_password_reset_token(
            user_id                = user.id,
            reset_token            = password_reset_token,
            reset_token_expiration = reset_token_expiration
        )

        return password_reset_token

    async def start_change_password(self, user_name: str, hours: int = 1):
        user = await self._users_repository.get_user(user_name)
        if not user:
            raise ValueError(TranslationService.t("common.error.userNotFound"))
        return await self._generate_passwd_reset_token(user, hours)

    async def _validate_reset_token(self, user: User):
        expiration = user.reset_token_expiration

        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        if expiration < datetime.now(timezone.utc):
            await self._users_repository.remove_password_reset_token(user.id)
            raise ValueError(TranslationService.t('common.error.invalidToken'))

        return user

    async def add_user(self, user_name: str, password: str):
        hashed = pwd_context.hash(password)
        await self._users_repository.force_create_user(user_name, hashed)

    async def cancel_change_password(self, user_name: str):
        user = await self._users_repository.get_user(user_name)
        if user is None:
            raise ValueError(TranslationService.t("common.error.userNotFound"))

        await self._users_repository.remove_password_reset_token(user.id)

    async def change_password(self, token: str, new_password: str):
        user = await self._users_repository.get_user_by_reset_token(token)
        if user is None:
            raise ValueError(TranslationService.t("common.error.userNotFound"))

        await self._validate_reset_token(user)

        hashed_new_password = pwd_context.hash(new_password)
        await self._users_repository.change_password(user.id, hashed_new_password)

    async def rename_user(self, user_id: int, user_name: str):
        await self._users_repository.rename_user(user_id, user_name)
