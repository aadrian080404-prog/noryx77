from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from core.sqlite_federated_audit import SQLiteFederatedAuditLog


def test_independent_audit_connections_serialize_concurrent_appends(tmp_path):
    path = tmp_path / "multi-writer-journal.sqlite"
    first = SQLiteFederatedAuditLog(path)
    second = SQLiteFederatedAuditLog(path)
    barrier = Barrier(2)

    def append(log, event):
        barrier.wait(timeout=10)
        return log.record(event, writer=event)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda pair: append(*pair),
                ((first, "writer-a"), (second, "writer-b")),
            ))

        assert {item["event"] for item in results} == {"writer-a", "writer-b"}
        assert first.verify_integrity() is True
        assert second.verify_integrity() is True
        snapshot = first.snapshot()
        assert len(snapshot) == 2
        assert {item["event"] for item in snapshot} == {"writer-a", "writer-b"}
        assert first.checkpoint() == second.checkpoint()
    finally:
        first.close()
        second.close()
