"""Tests for app/services/push/fcm_sender.py."""
from unittest.mock import MagicMock, patch

import pytest
from firebase_admin import messaging

from app.services.push import fcm_sender
from app.services.push.fcm_sender import FcmSender, PushMessage


def _sender(credentials='{"type": "service_account"}') -> FcmSender:
    settings = MagicMock()
    settings.FIREBASE_CREDENTIALS = credentials
    return FcmSender(settings)


def _response(success: bool, exception=None):
    item = MagicMock()
    item.success = success
    item.exception = exception
    return item


class TestFcmSender:
    @pytest.mark.asyncio
    async def test_not_configured_skips_sending(self):
        sender = _sender(credentials=None)
        with patch.object(messaging, "send_each_for_multicast") as send:
            result = await sender.send(["a"], PushMessage(title="t", body="b"))
        send.assert_not_called()
        assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_empty_tokens(self):
        result = await _sender().send([], PushMessage(title="t", body="b"))
        assert result.success_count == 0 and result.failure_count == 0

    @pytest.mark.asyncio
    async def test_collects_unregistered_tokens(self):
        sender = _sender()
        sender._get_app = MagicMock()
        batch = MagicMock()
        batch.success_count = 1
        batch.failure_count = 2
        batch.responses = [
            _response(True),
            _response(False, messaging.UnregisteredError("gone")),
            _response(False, Exception("temporary")),
        ]

        with patch.object(messaging, "send_each_for_multicast", return_value=batch):
            result = await sender.send(["a", "b", "c"], PushMessage(title="t", body="b", data={"route": "/"}))

        assert result.success_count == 1
        assert result.failure_count == 2
        assert result.invalid_tokens == ["b"]

    @pytest.mark.asyncio
    async def test_splits_into_batches(self):
        sender = _sender()
        sender._get_app = MagicMock()
        sizes = []

        def fake_send(message, app=None):
            sizes.append(len(message.tokens))
            batch = MagicMock()
            batch.success_count = len(message.tokens)
            batch.failure_count = 0
            batch.responses = [_response(True)] * len(message.tokens)
            return batch

        tokens = [f"t{i}" for i in range(fcm_sender.FCM_BATCH_SIZE + 3)]
        with patch.object(messaging, "send_each_for_multicast", side_effect=fake_send):
            result = await sender.send(tokens, PushMessage(title="t", body="b"))

        assert sizes == [fcm_sender.FCM_BATCH_SIZE, 3]
        assert result.success_count == len(tokens)
