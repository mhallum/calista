"""Contract tests for the StreamIndex port."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Literal

import pytest

from calista.adapters.eventstore.stream_index import SqlAlchemyStreamIndex
from calista.interfaces.stream_index import (
    IndexEntry,
    NaturalKey,
    NaturalKeyAlreadyBound,
)

# Deal with pytest fixtures
# pylint: disable=redefined-outer-name

# --- Test utilities


@pytest.fixture(params=["sql_file", "postgres"])
def make_stream_index_ctx(
    request: pytest.FixtureRequest,
    sqlite_engine_file,
    postgres_engine,
):
    """Factory for context managers yielding a StreamIndex instance.

    Each context manager provides a new connection + transaction.
    The fixture is parameterized to test different concurrency-safe backends.
    """

    @contextmanager
    def _ctx():
        # New connection + BEGIN; COMMIT on context exit (or ROLLBACK on error)
        match request.param:
            case "sql_file":
                with sqlite_engine_file.begin() as conn:
                    yield SqlAlchemyStreamIndex(conn)
            case "postgres":
                with postgres_engine.begin() as conn:
                    yield SqlAlchemyStreamIndex(conn)
            case _:
                raise ValueError(f"unknown store type: {request.param}")

    return _ctx


# # --- Concurrency contracts -------------------------------------------------
# # These assert the adapter relies on storage-level uniqueness to arbitrate races.


# @pytest.mark.contract_concurrency
def test_concurrent_reserve_same_key_same_stream_id(make_stream_index_ctx):
    """Multiple threads reserving the same (key, stream_id) pair all succeed."""
    key = NaturalKey("ObservationSession", "SITE/2024-02-01/INST/R001")
    stream_id = "01HZZZ1111111111XXXXXX7"

    barrier = threading.Barrier(8)
    results: list[tuple[Literal["ok", "err"], IndexEntry | Exception]] = []
    lock = threading.Lock()  # protect results append

    def worker():
        with make_stream_index_ctx() as idx:
            try:  # pylint: disable=too-many-try-statements
                barrier.wait(timeout=5)
                result = idx.reserve(key, stream_id)
                with lock:
                    results.append(("ok", result))
            except NaturalKeyAlreadyBound as e:
                with lock:
                    results.append(("err", e))
            except threading.BrokenBarrierError as e:
                with lock:
                    results.append(("err", e))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    oks = [r for tag, r in results if tag == "ok"]
    assert len(oks) == len(results), f"unexpected errors: {results}"

    # check the binding once with a fresh index (new connection)
    with make_stream_index_ctx() as idx_check:
        found = idx_check.lookup(key)
        assert found and found.stream_id == stream_id


def test_concurrent_reserve_same_key_different_stream_ids(make_stream_index_ctx):
    """Multiple threads reserving the same key with different stream_ids.

    Exactly one should succeed; the rest should raise NaturalKeyAlreadyBound.
    """
    key = NaturalKey("obs_session", "SITE/2024-02-02/INST/R002")
    stream_ids = [f"01HZZZ2222{i:02d}XXXXXX8" for i in range(8)]

    barrier = threading.Barrier(8)
    results: list[tuple[Literal["ok", "err"], str | Exception]] = []
    lock = threading.Lock()  # protect results append

    def worker(my_id: str):
        with make_stream_index_ctx() as idx:
            try:  # pylint: disable=too-many-try-statements
                barrier.wait(timeout=5)
                idx.reserve(key, my_id)
                with lock:
                    results.append(("ok", my_id))
            except NaturalKeyAlreadyBound as e:
                with lock:
                    results.append(("err", e))
            except threading.BrokenBarrierError as e:
                with lock:
                    results.append(("err", e))

    threads = [threading.Thread(target=worker, args=(sid,)) for sid in stream_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    oks = [sid for tag, sid in results if tag == "ok"]
    errs = [sid for tag, sid in results if tag == "err"]

    # Exactly one winner; the rest must observe the conflict.
    expected_n_oks = 1
    expected_n_errs = 7
    assert len(oks) == expected_n_oks, f"expected exactly one winner, got {oks}"
    assert len(errs) == expected_n_errs, f"expected seven conflicts, got {errs}"

    winner_stream_id = oks[0]
    # check the binding once with a fresh index (new connection)
    with make_stream_index_ctx() as idx_check:
        found = idx_check.lookup(key)
        assert found is not None
        assert found.stream_id == winner_stream_id
