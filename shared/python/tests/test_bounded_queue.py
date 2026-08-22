"""Tests for shared/bounded_queue.py."""
import asyncio
import threading

import pytest

from shared.bounded_queue import BoundedQueue


class TestBoundedQueueInit:
    def test_default_maxsize(self):
        q = BoundedQueue()
        assert q.maxsize == 100

    def test_custom_maxsize(self):
        q = BoundedQueue(maxsize=50)
        assert q.maxsize == 50

    def test_default_deduplicate(self):
        q = BoundedQueue()
        assert q.deduplicate is True

    def test_custom_deduplicate(self):
        q = BoundedQueue(deduplicate=False)
        assert q.deduplicate is False

    def test_last_item_initially_none(self):
        q = BoundedQueue()
        assert q.last_item is None

    def test_data_is_deque(self):
        from collections import deque
        q = BoundedQueue()
        assert isinstance(q.data, deque)

    def test_cv_is_condition(self):
        q = BoundedQueue()
        assert isinstance(q.cv, threading.Condition)

    def test_async_cv_is_condition(self):
        q = BoundedQueue()
        assert isinstance(q.async_cv, asyncio.Condition)


class TestPutNowait:
    def test_put_single_item(self):
        q = BoundedQueue()
        q.put_nowait("item1")
        assert len(q) == 1
        assert q.last_item == "item1"

    def test_put_multiple_items(self):
        q = BoundedQueue()
        q.put_nowait("item1")
        q.put_nowait("item2")
        assert len(q) == 2

    def test_deduplicate_same_item(self):
        q = BoundedQueue(deduplicate=True)
        q.put_nowait("item1")
        q.put_nowait("item1")
        assert len(q) == 1

    def test_no_deduplicate_same_item(self):
        q = BoundedQueue(deduplicate=False)
        q.put_nowait("item1")
        q.put_nowait("item1")
        assert len(q) == 2

    def test_deduplicate_different_items(self):
        q = BoundedQueue(deduplicate=True)
        q.put_nowait("item1")
        q.put_nowait("item2")
        assert len(q) == 2

    def test_maxsize_enforced(self):
        q = BoundedQueue(maxsize=3)
        q.put_nowait("a")
        q.put_nowait("b")
        q.put_nowait("c")
        q.put_nowait("d")
        assert len(q) == 3
        assert "a" not in q.data


class TestGet:
    def test_get_returns_item(self):
        q = BoundedQueue()
        q.put_nowait("item1")
        result = q.get()
        assert result == "item1"
        assert len(q) == 0

    def test_get_blocks_when_empty(self):
        q = BoundedQueue()
        result = []

        def consumer():
            result.append(q.get())

        t = threading.Thread(target=consumer)
        t.start()
        # Give the thread time to block
        import time
        time.sleep(0.1)
        q.put_nowait("item1")
        t.join(timeout=2)
        assert result == ["item1"]


class TestAsyncPut:
    @pytest.mark.asyncio
    async def test_async_put_single_item(self):
        q = BoundedQueue()
        await q.async_put("item1")
        assert len(q) == 1
        assert q.last_item == "item1"

    @pytest.mark.asyncio
    async def test_async_put_deduplicate(self):
        q = BoundedQueue(deduplicate=True)
        await q.async_put("item1")
        await q.async_put("item1")
        assert len(q) == 1

    @pytest.mark.asyncio
    async def test_async_put_no_deduplicate(self):
        q = BoundedQueue(deduplicate=False)
        await q.async_put("item1")
        await q.async_put("item1")
        assert len(q) == 2


class TestAsyncGet:
    @pytest.mark.asyncio
    async def test_async_get_returns_item(self):
        q = BoundedQueue()
        await q.async_put("item1")
        result = await q.async_get()
        assert result == "item1"
        assert len(q) == 0

    @pytest.mark.asyncio
    async def test_async_get_blocks_when_empty(self):
        q = BoundedQueue()

        async def consumer():
            return await q.async_get()

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        await q.async_put("item1")
        result = await asyncio.wait_for(task, timeout=2)
        assert result == "item1"


class TestLen:
    def test_len_empty(self):
        q = BoundedQueue()
        assert len(q) == 0

    def test_len_after_put(self):
        q = BoundedQueue()
        q.put_nowait("a")
        q.put_nowait("b")
        assert len(q) == 2

    def test_len_after_get(self):
        q = BoundedQueue()
        q.put_nowait("a")
        q.get()
        assert len(q) == 0


class TestNotifyAsync:
    @pytest.mark.asyncio
    async def test_notify_async_no_waiters(self):
        q = BoundedQueue()
        # Should not raise even with no waiters
        await q._notify_async()
