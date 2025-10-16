"""Contract tests for IdGenerator implementations which ensure monotonicity."""

import concurrent.futures as cf
import time

import pytest


@pytest.mark.parametrize("count", [2_000, 10_000])
def test_monotonic_order_single_thread(monotonic_id_generators, count):
    """IDs are lexicographically non-decreasing when generated in a single thread."""
    ids = [monotonic_id_generators.new_id() for _ in range(count)]
    assert ids == sorted(ids), "IDs must be lexicographically non-decreasing"


def test_monotonic_order_under_threads(monotonic_id_generators):
    """IDs are lexicographically non-decreasing when generated from multiple threads."""
    num_ids = 8000
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        # record generation timestamp immediately after new_id() returns
        futures = [
            ex.submit(
                lambda: (
                    monotonic_id_generators.new_id(),
                    time.time_ns(),
                )
            )
            for _ in range(num_ids)
        ]
        results = [f.result() for f in cf.as_completed(futures)]

    # sort by the recorded generation timestamp, use id as tie-breaker
    results.sort(key=lambda r: (r[1], r[0]))
    ids_by_generation = [r[0] for r in results]

    assert ids_by_generation == sorted(ids_by_generation), (
        "IDs must be non-decreasing in generation order (sorted by generation timestamp)"
    )
