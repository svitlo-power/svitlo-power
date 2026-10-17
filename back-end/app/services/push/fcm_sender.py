import asyncio
import json
import logging
import os
from dataclasses import dataclass, field

import firebase_admin
from firebase_admin import credentials, messaging
from injector import inject

from app.settings import Settings


logger = logging.getLogger(__name__)

# FCM accepts at most 500 tokens per multicast request
FCM_BATCH_SIZE = 500

APP_NAME = "svitlo-power-push"


@dataclass
class PushMessage:
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@dataclass
class FcmSendResult:
    success_count: int = 0
    failure_count: int = 0
    invalid_tokens: list[str] = field(default_factory=list)


@inject
class FcmSender:
    def __init__(self, settings: Settings):
        self._credentials = settings.FIREBASE_CREDENTIALS
        self._app: firebase_admin.App | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._credentials)

    def _get_app(self) -> firebase_admin.App:
        if self._app:
            return self._app

        try:
            self._app = firebase_admin.get_app(APP_NAME)
            return self._app
        except ValueError:
            pass

        raw = self._credentials.strip()
        if raw.startswith("{"):
            cert = credentials.Certificate(json.loads(raw))
        elif os.path.isfile(raw):
            cert = credentials.Certificate(raw)
        else:
            raise RuntimeError("FIREBASE_CREDENTIALS must be a service account JSON or a path to it")

        self._app = firebase_admin.initialize_app(cert, name=APP_NAME)
        return self._app

    def _build_multicast(self, tokens: list[str], message: PushMessage) -> messaging.MulticastMessage:
        return messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(title=message.title, body=message.body),
            data=message.data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(channel_id="default"),
            ),
        )

    def _send_batch(self, tokens: list[str], message: PushMessage) -> FcmSendResult:
        response = messaging.send_each_for_multicast(
            self._build_multicast(tokens, message),
            app=self._get_app(),
        )

        result = FcmSendResult(
            success_count=response.success_count,
            failure_count=response.failure_count,
        )
        for token, item in zip(tokens, response.responses):
            if item.success:
                continue
            if isinstance(item.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
                result.invalid_tokens.append(token)
            else:
                logger.warning(f"FCM send failed: {item.exception}")
        return result

    async def send(self, tokens: list[str], message: PushMessage) -> FcmSendResult:
        total = FcmSendResult()
        if not tokens:
            return total

        if not self.is_configured:
            logger.warning("FIREBASE_CREDENTIALS is not set, push notifications are disabled")
            total.failure_count = len(tokens)
            return total

        for i in range(0, len(tokens), FCM_BATCH_SIZE):
            batch = tokens[i:i + FCM_BATCH_SIZE]
            # firebase-admin is synchronous, keep it off the event loop
            result = await asyncio.to_thread(self._send_batch, batch, message)
            total.success_count += result.success_count
            total.failure_count += result.failure_count
            total.invalid_tokens.extend(result.invalid_tokens)

        return total
