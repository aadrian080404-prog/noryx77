"""End-to-end tests for quorum-backed durable SQLite audit checkpoints."""
import os
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from core.journal_integrity import AnchorSnapshot, ZERO_MAC
from core.quorum_witness import QuorumMonotonicAnchor
from core.remote_witness import RemoteMonotonicAnchor
from core.sqlite_audit import SQLiteAuditLog
from core.witness_authority import InProcessWitnessClient, SQLiteWitnessAuthority


def make_quorum(tmp_path):
    anchors = []
    authorities = []
    for index in range(3):
        key = Ed25519PrivateKey.generate()
        authority = SQLiteWitnessAuthority(
            str(tmp_path / f"witness-{index}.sqlite"),
            witness_id=f"witness-{index}",
            signing_key=key,
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"witness-{index}",
            trusted_public_key=key.public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw
            ),
            failure_domain=f"failure-domain-{index}",
        ))
    return QuorumMonotonicAnchor({
        f"witness-{i}": anchor for i, anchor in enumerate(anchors)
    }), authorities


def close_all(authorities):
    for authority in authorities:
        authority.close()


def test_sqlite_audit_advances_and_recovers_through_quorum(tmp_path):
    quorum, authorities = make_quorum(tmp_path)
    path = str(tmp_path / "audit.sqlite")
    audit = SQLiteAuditLog(path)
    audit.record("first")
    first = audit.verify_and_advance_anchor(quorum)
    assert first.sequence == 1
    audit.record("second")
    audit.record("third")
    second = audit.verify_and_advance_anchor(quorum)
    assert second.sequence == 3
    assert quorum.read() == second
    audit.close()

    reopened = SQLiteAuditLog(path)
    assert reopened.verify_and_advance_anchor(quorum) == second
    assert reopened.verify_integrity()
    reopened.close()
    close_all(authorities)


def test_sqlite_audit_rejects_rollback_against_quorum(tmp_path):
    quorum, authorities = make_quorum(tmp_path)
    path = str(tmp_path / "audit.sqlite")
    old_copy = str(tmp_path / "old-audit.sqlite")
    audit = SQLiteAuditLog(path)
    audit.record("anchored-1")
    first = audit.verify_and_advance_anchor(quorum)
    source = sqlite3.connect(path)
    destination = sqlite3.connect(old_copy)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    audit.record("anchored-2")
    second = audit.verify_and_advance_anchor(quorum)
    assert second.sequence == first.sequence + 1
    audit.close()

    for suffix in ("-wal", "-shm"):
        sidecar = path + suffix
        if os.path.exists(sidecar):
            os.remove(sidecar)
    os.replace(old_copy, path)
    restored = SQLiteAuditLog(path)
    with pytest.raises(ValueError, match="audit_database_rollback_detected"):
        restored.verify_and_advance_anchor(quorum)
    restored.close()
    close_all(authorities)


def test_sqlite_audit_recovers_after_partial_quorum_advance(tmp_path):
    quorum, authorities = make_quorum(tmp_path)
    path = str(tmp_path / "partial-audit.sqlite")
    audit = SQLiteAuditLog(path)
    audit.record("event-1")
    audit.record("event-2")
    audit.record("event-3")

    class InterruptAfterFirstAdvance:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.advances = 0

        def read(self):
            return self.wrapped.read()

        def compare_and_swap(self, expected, replacement):
            self.advances += 1
            if self.advances == 2:
                return False
            return self.wrapped.compare_and_swap(expected, replacement)

    interrupted = InterruptAfterFirstAdvance(quorum)
    with pytest.raises(ValueError, match="audit_anchor_compare_and_swap_failed"):
        audit.verify_and_advance_anchor(interrupted)

    partial = quorum.read()
    assert partial.sequence == 1
    audit.close()

    reopened = SQLiteAuditLog(path)
    recovered = reopened.verify_and_advance_anchor(quorum)
    assert recovered.sequence == 3
    assert quorum.read() == recovered
    assert reopened.verify_integrity()

    reopened.close()
    close_all(authorities)



def test_sqlite_audit_serializes_concurrent_independent_writers(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = str(tmp_path / "concurrent-audit.sqlite")
    first = SQLiteAuditLog(path)
    second = SQLiteAuditLog(path)

    def write_batch(log, prefix):
        for index in range(20):
            log.record("concurrent_event", writer=prefix, index=index)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(write_batch, first, "first"),
            pool.submit(write_batch, second, "second"),
        )
        for future in futures:
            future.result(timeout=15)

    assert len(first.snapshot()) == 40
    assert first.verify_integrity()
    assert second.verify_integrity()
    assert first.digest() == second.digest()

    first.close()
    second.close()


def _multiprocess_audit_writer(database_path, writer_id, event_count):
    """Top-level worker so the test also runs with multiprocessing spawn."""
    audit = SQLiteAuditLog(database_path, busy_timeout_ms=15000)
    try:
        for index in range(event_count):
            audit.record("multiprocess_event", writer=writer_id, index=index)
    finally:
        audit.close()


def test_sqlite_audit_serializes_independent_process_writers(tmp_path):
    import multiprocessing

    path = str(tmp_path / "multiprocess-audit.sqlite")
    context = multiprocessing.get_context("spawn")
    workers = [
        context.Process(
            target=_multiprocess_audit_writer,
            args=(path, f"writer-{index}", 12),
        )
        for index in range(3)
    ]

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
    try:
        assert all(not worker.is_alive() for worker in workers), "audit_writer_process_timeout"
        assert [worker.exitcode for worker in workers] == [0, 0, 0]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)

    audit = SQLiteAuditLog(path)
    events = audit.snapshot()
    assert len(events) == 36
    assert audit.verify_integrity()
    independent = SQLiteAuditLog(path)
    assert independent.digest() == audit.digest()
    assert independent.verify_integrity()
    independent.close()
    counts = {}
    for event in events:
        counts[event["writer"]] = counts.get(event["writer"], 0) + 1
    assert counts == {"writer-0": 12, "writer-1": 12, "writer-2": 12}
    audit.close()
