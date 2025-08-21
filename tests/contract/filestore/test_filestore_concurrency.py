"""Concurrency deduplication contract test for the CAS filestore.

This test stresses the commit path by making multiple writers stage identical
bytes, then *simultaneously* attempt `commit()` using a Barrier+Event sync.
It asserts that all writers observe the same digest and that the object
round-trips correctly. Timeouts ensure failures don’t hang the test.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from threading import Barrier, BrokenBarrierError, Event

import pytest

from calista.adapters.filestore.api import AbstractFileStore


def test_concurrent_commit_dedup(store: AbstractFileStore, arbitrary_bytes: bytes):
    """Concurrent writers committing identical bytes deduplicate to one object.

    Setup:
      - Spawn N workers.
      - Each worker stages the same payload with `open_write().write(...)`.
      - All workers block on a barrier to align just before `commit()`.
      - Main thread releases them with an Event so they race the critical section.

    Expectations:
      - All commits return the *same* digest.
      - The digest exists in the store and round-trips to the original bytes.
      - Timeouts and barrier errors fail fast (no indefinite hangs).
    """

    n = 16
    ready = Barrier(n + 1)  # include main thread
    go = Event()

    def worker() -> str:
        with store.open_write() as w:
            w.write(arbitrary_bytes)
            # single-statement try: only the wait can raise BrokenBarrierError
            try:
                ready.wait(timeout=5)
            except BrokenBarrierError as e:
                pytest.fail(f"Barrier broken in worker: {e!r}")
            # single call; Event.wait returns bool (False on timeout)
            assert go.wait(timeout=5)
            return w.commit().digest

    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(worker) for _ in range(n)]

        # single-statement try: main also waits on the same barrier
        try:
            ready.wait(timeout=5)
        except BrokenBarrierError as e:
            pytest.fail(f"Barrier broken in main: {e!r}")

        go.set()  # release all workers to race the commit

        digests: list[str] = []
        # single-statement try: as_completed may raise TimeoutError
        try:  # pylint: disable=too-many-try-statements
            for f in as_completed(futures, timeout=10):
                # let individual worker exceptions surface normally here
                digests.append(f.result())
        except FuturesTimeoutError:
            pytest.fail("Timed out waiting for concurrent workers to finish")

    # Assertions
    d0 = digests[0]
    assert all(d == d0 for d in digests)
    assert store.exists(d0)
    assert store.readall(d0) == arbitrary_bytes
