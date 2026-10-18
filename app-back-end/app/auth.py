import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request, status


APP_TOKEN_HEADER = "X-App-Token"


async def verify_app_token(
    request: Request,
    x_app_token: Optional[str] = Header(default=None, alias=APP_TOKEN_HEADER),
):
    expected = request.app.state.settings.APP_ACCESS_TOKEN
    if not expected:
        return
    if not x_app_token or not secrets.compare_digest(x_app_token.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid app token")
