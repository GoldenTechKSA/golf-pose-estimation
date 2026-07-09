"""Wall-clock timing for pipeline stages.

The progress spans in the pipeline were assigned by hand, not measured, so the
question "where does an analysis actually spend its time?" had no answer. These
helpers record per-stage seconds and emit them as one grep-able line per job.
"""
from contextlib import contextmanager
from time import perf_counter


@contextmanager
def record(into: dict[str, float], key: str):
    """Time the block and store the elapsed seconds under `key`."""
    start = perf_counter()
    try:
        yield
    finally:
        into[key] = round(perf_counter() - start, 3)


def format_timings(**fields) -> str:
    """Render `key=value` pairs in a stable order for a single log line."""
    return " ".join(f"{k}={v}" for k, v in fields.items())
