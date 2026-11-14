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

def test_sqlite_audit_rejects_noncanonical_external_anchor_mac(tmp_path):
    audit = SQLiteAuditLog(str(tmp_path / "malformed-anchor.sqlite"))

    class MalformedAnchor:
        def read(self):
            return AnchorSnapshot(0, "aa" * 31 + "  ")

        def compare_and_swap(self, expected, replacement):
            raise AssertionError("unexpected_compare_and_swap")

    try:
        with pytest.raises(ValueError, match="audit_anchor_snapshot_invalid"):
            audit.verify_and_advance_anchor(MalformedAnchor())
    finally:
        audit.close()

def _crash_during_uncommitted_audit_append(database_path):
    connection = sqlite3.connect(database_path, isolation_level=None)
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        "INSERT INTO audit_events(event_json, digest) VALUES (?, ?)",
        ('{"event":"uncommitted-crash-probe"}', "0" * 64),
    )
    # Simulate abrupt process death: no Python finally block and no ROLLBACK.
    os._exit(73)


def test_sqlite_audit_recovers_uncommitted_transaction_after_process_death(tmp_path):
    import multiprocessing

    path = str(tmp_path / "crash-recovery.sqlite")
    audit = SQLiteAuditLog(path)
    audit.record("durable-before-crash", marker="preserved")
    expected_digest = audit.digest()
    audit.close()

    context = multiprocessing.get_context("spawn")
    worker = context.Process(target=_crash_during_uncommitted_audit_append, args=(path,))
    worker.start()
    worker.join(timeout=20)
    try:
        assert not worker.is_alive(), "crash_probe_process_timeout"
        assert worker.exitcode == 73
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)

    recovered = SQLiteAuditLog(path)
    assert recovered.snapshot() == ({"event": "durable-before-crash", "marker": "preserved"},)
    assert recovered.digest() == expected_digest
    assert recovered.verify_integrity()
    recovered.close()



def _crash_after_external_anchor_advance(audit_path, database_paths, private_keys):
    """Terminate immediately after the first durable external witness majority."""
    import os
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from core.quorum_witness import QuorumMonotonicAnchor
    from core.remote_witness import RemoteMonotonicAnchor
    from core.sqlite_audit import SQLiteAuditLog
    from core.witness_authority import InProcessWitnessClient, SQLiteWitnessAuthority

    authorities = []
    anchors = []
    for index, (database_path, raw_key) in enumerate(zip(database_paths, private_keys)):
        key = Ed25519PrivateKey.from_private_bytes(raw_key)
        authority = SQLiteWitnessAuthority(
            database_path, witness_id=f"witness-{index}", signing_key=key
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"witness-{index}",
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain=f"failure-domain-{index}",
        ))
    quorum = QuorumMonotonicAnchor({
        f"witness-{index}": anchor for index, anchor in enumerate(anchors)
    })

    class CrashAfterFirstCommit:
        def read(self):
            return quorum.read()

        def compare_and_swap(self, expected, replacement):
            accepted = quorum.compare_and_swap(expected, replacement)
            if accepted:
                os._exit(79)
            return False

    audit = SQLiteAuditLog(audit_path)
    audit.verify_and_advance_anchor(CrashAfterFirstCommit())


def test_sqlite_audit_recovers_process_death_during_external_anchor_advancement(tmp_path):
    import multiprocessing
    from cryptography.hazmat.primitives.serialization import PrivateFormat, NoEncryption

    audit_path = str(tmp_path / "external-anchor-crash-audit.sqlite")
    database_paths = [str(tmp_path / f"external-anchor-witness-{index}.sqlite") for index in range(3)]
    private_keys = []
    authorities = []
    for index, database_path in enumerate(database_paths):
        key = Ed25519PrivateKey.generate()
        private_keys.append(key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        ))
        authorities.append(SQLiteWitnessAuthority(
            database_path, witness_id=f"witness-{index}", signing_key=key
        ))
    audit = SQLiteAuditLog(audit_path)
    audit.record("checkpoint-1")
    audit.record("checkpoint-2")
    audit.record("checkpoint-3")
    expected_head = AnchorSnapshot(3, audit.digest())
    audit.close()
    close_all(authorities)

    context = multiprocessing.get_context("spawn")
    worker = context.Process(
        target=_crash_after_external_anchor_advance,
        args=(audit_path, database_paths, private_keys),
    )
    worker.start()
    worker.join(timeout=30)
    try:
        assert not worker.is_alive(), "external_anchor_crash_process_timeout"
        assert worker.exitcode == 79
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)

    recovery_authorities = []
    recovery_anchors = []
    for index, database_path in enumerate(database_paths):
        key = Ed25519PrivateKey.from_private_bytes(private_keys[index])
        authority = SQLiteWitnessAuthority(
            database_path, witness_id=f"witness-{index}", signing_key=key
        )
        recovery_authorities.append(authority)
        recovery_anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"witness-{index}",
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain=f"failure-domain-{index}",
        ))
    try:
        quorum = QuorumMonotonicAnchor({
            f"witness-{index}": anchor for index, anchor in enumerate(recovery_anchors)
        })
        partial = quorum.read()
        prefix = SQLiteAuditLog(audit_path)
        first_prefix = prefix._rows()[0][2]
        prefix.close()
        assert partial == AnchorSnapshot(1, first_prefix)
        reopened = SQLiteAuditLog(audit_path)
        assert reopened.verify_and_advance_anchor(quorum) == expected_head
        assert quorum.read() == expected_head
        assert reopened.verify_integrity()
        reopened.close()
    finally:
        close_all(recovery_authorities)


def test_independent_audit_writers_converge_on_same_external_anchor(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    quorum, authorities = make_quorum(tmp_path)
    second_quorum = QuorumMonotonicAnchor({
        f"witness-{index}": anchor
        for index, anchor in enumerate(quorum._witnesses.values())
    })
    path = str(tmp_path / "concurrent-anchor-audit.sqlite")
    seed = SQLiteAuditLog(path)
    seed.record("shared-event-1")
    seed.record("shared-event-2")
    seed.record("shared-event-3")
    expected_sequence = len(seed.snapshot())
    seed.close()

    first_log = SQLiteAuditLog(path)
    second_log = SQLiteAuditLog(path)
    barrier = Barrier(3)

    def advance(log, anchor):
        barrier.wait(timeout=10)
        return log.verify_and_advance_anchor(anchor)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(advance, first_log, quorum)
            second = pool.submit(advance, second_log, second_quorum)
            barrier.wait(timeout=10)
            first_head = first.result(timeout=20)
            second_head = second.result(timeout=20)
        assert first_head == second_head
        assert first_head.sequence == expected_sequence
        assert quorum.read() == first_head
        assert second_quorum.read() == first_head
        assert first_log.verify_integrity()
        assert second_log.verify_integrity()
    finally:
        first_log.close()
        second_log.close()
        close_all(authorities)


def test_sqlite_audit_resolves_lost_quorum_cas_ack_by_authenticated_readback(tmp_path):
    """A committed majority with a lost reply is success only after read-back."""
    quorum, authorities = make_quorum(tmp_path)
    audit = SQLiteAuditLog(str(tmp_path / "lost-quorum-ack-audit.sqlite"))

    class LoseReplyAfterCommit:
        def read(self):
            return quorum.read()

        def compare_and_swap(self, expected, replacement):
            accepted = quorum.compare_and_swap(expected, replacement)
            if accepted:
                raise OSError("reply_lost_after_quorum_commit")
            return accepted

    try:
        audit.record("commit-before-reply-loss")
        expected = AnchorSnapshot(1, audit.digest())
        assert audit.verify_and_advance_anchor(LoseReplyAfterCommit()) == expected
        assert quorum.read() == expected
        assert audit.verify_integrity()
    finally:
        audit.close()
        close_all(authorities)
