import asyncio
import json
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from shared import BoundedQueue
from shared.services import EventsService
from shared.utils.jwt_utils import InvalidTokenError, decode_jwt
from app.settings import Settings


def make_get_claims(settings: Settings):
    def get_claims(token: str | None = Query(default=None)):
        if token is None:
            return None
        try:
            return decode_jwt(token, settings.JWT_SECRET_KEY)
        except InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired JWT token",
            )
    return get_claims


def register(app: FastAPI, service: EventsService, settings: Settings):
    get_claims = make_get_claims(settings)

    @app.get("/api/events")
    async def events(
        claims: dict | None = Depends(get_claims)
    ):
        q = BoundedQueue(maxsize=100)

        user = claims["sub"] if claims else None
        is_auth = user is not None

        service.add_public_client(q)
        if is_auth:
            service.add_private_client(q)

        async def event_generator():
            try:
                while True:
                    event = await q.async_get()
                    if event is None:
                        break

                    if event.private and not is_auth:
                        continue

                    if user:
                        event.user = user

                    yield f"data: {json.dumps(event.to_dict())}\n\n"

                    if event.type == "shutdown":
                        await asyncio.sleep(0)
                        break
            finally:
                service.remove_client(q)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
