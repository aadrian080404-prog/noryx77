from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from core.offline_anchor import MonotonicAnchor


def test_concurrent_connections_cannot_roll_back_highest_epoch(tmp_path):
    path = str(tmp_path / "shared-anchor.db")
    low = MonotonicAnchor(path)
    high = MonotonicAnchor(path)
    start = Barrier(3)

    def accept(anchor, epoch, snapshot_id):
        start.wait(timeout=5)
        return anchor.accept(epoch, snapshot_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            low_future = pool.submit(accept, low, 800, "snapshot-800")
            high_future = pool.submit(accept, high, 900, "snapshot-900")
            start.wait(timeout=5)
            low_future.result(timeout=10)
            high_future.result(timeout=10)

        assert high.current() == (900, "snapshot-900")
        assert low.accept(899, "snapshot-899") is False
        assert high.current() == (900, "snapshot-900")
    finally:
        low.close()
        high.close()
