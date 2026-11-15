from concurrent.futures import ThreadPoolExecutor

from core.audit import AuditLog
from core.crypto import InMemoryKeyProvider, KEY_SIZE


def test_concurrent_records_preserve_audit_chain():
    log = AuditLog()

    def record(index):
        log.record("concurrent_event", index=index)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(record, range(500)))

    snapshot = log.snapshot()
    assert len(snapshot) == 500
    assert log.verify_integrity()
    assert len({entry["index"] for entry in snapshot}) == 500


def test_checkpoint_is_bound_to_a_consistent_chain_head():
    log = AuditLog()
    provider = InMemoryKeyProvider({"audit": b"K" * KEY_SIZE})
    log.record("before")
    checkpoint = log.checkpoint(provider, key_id="audit")
    assert log.verify_checkpoint(checkpoint, provider)
    log.record("after")
    assert not log.verify_checkpoint(checkpoint, provider)


def test_concurrent_record_and_snapshot_never_exposes_partial_chain():
    log = AuditLog()

    def writer(offset):
        for index in range(100):
            log.record("event", index=offset + index)

    def reader():
        for _ in range(100):
            log.snapshot()
            assert log.verify_integrity()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(writer, n * 100) for n in range(4)]
        futures.extend(pool.submit(reader) for _ in range(4))
        for future in futures:
            future.result()

    assert len(log.snapshot()) == 400
    assert log.verify_integrity()
