from __future__ import annotations

from filelock import FileLock, Timeout


def test_overlapping_run_is_prevented(tmp_path) -> None:
    first = FileLock(tmp_path / "agent.lock", timeout=0)
    second = FileLock(tmp_path / "agent.lock", timeout=0)
    with first:
        try:
            second.acquire()
        except Timeout:
            pass
        else:
            raise AssertionError("second lock unexpectedly acquired")
