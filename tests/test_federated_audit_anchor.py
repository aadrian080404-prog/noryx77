import sqlite3

import pytest

from core.federated_audit_anchor import (
    AnchoredFederatedAuditSink,
    FederatedAuditCheckpoint,
    FederatedAuditSynchronizer,
    SQLiteFederatedAuditWriterLease,
)
from core.sqlite_federated_audit import SQLiteFederatedAuditLog


class FakeAnchor:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint

    def read_checkpoint(self, namespace):
        return self.checkpoint

    def compare_and_advance(self, namespace, expected, next_checkpoint):
        if self.checkpoint != expected:
            return False
        self.checkpoint = next_checkpoint
        return True


def _log(path):
    return SQLiteFederatedAuditLog(path)


def test_federated_audit_external_anchor_records_first_event(tmp_path):
    log = _log(tmp_path / "federated-anchor.db")
    genesis = log.checkpoint()
    assert genesis.sequence == 0
    anchor = FakeAnchor(genesis)
    sync = FederatedAuditSynchronizer(log, anchor, namespace="noryx7/federation-a")
    log.record("dispatch_allowed", action_digest="a" * 64)
    checkpoint = sync.synchronize()
    assert checkpoint.sequence == 1
    assert anchor.checkpoint == checkpoint


def test_federated_audit_external_anchor_recovers_one_append_after_restart(tmp_path):
    db = tmp_path / "federated-anchor-restart.db"
    log = _log(db)
    anchor = FakeAnchor(log.checkpoint())
    sync = FederatedAuditSynchronizer(log, anchor, namespace="noryx7/federation-a")
    log.record("dispatch_allowed", action_digest="a" * 64)
    first = sync.synchronize()
    log.record("dispatch_completed", action_digest="a" * 64)
    log.close()

    restarted = _log(db)
    second = FederatedAuditSynchronizer(
        restarted, anchor, namespace="noryx7/federation-a"
    ).synchronize()
    assert second.sequence == first.sequence + 1
    assert anchor.checkpoint == second


def test_federated_audit_external_anchor_rejects_multirow_gap(tmp_path):
    log = _log(tmp_path / "federated-anchor-gap.db")
    anchor = FakeAnchor(log.checkpoint())
    sync = FederatedAuditSynchronizer(log, anchor, namespace="noryx7/federation-a")
    log.record("one", action_digest="1" * 64)
    log.record("two", action_digest="2" * 64)
    with pytest.raises(PermissionError, match="external_federated_audit_checkpoint_gap_exceeded"):
        sync.synchronize()


def test_federated_audit_external_anchor_detects_rollback(tmp_path):
    db = tmp_path / "federated-anchor-rollback.db"
    log = _log(db)
    log.record("one", action_digest="1" * 64)
    first = log.checkpoint()
    log.record("two", action_digest="2" * 64)
    second = log.checkpoint()
    anchor = FakeAnchor(second)

    connection = sqlite3.connect(db)
    try:
        connection.execute(
            "DROP TRIGGER IF EXISTS federated_audit_no_delete"
        )
        connection.execute(
            "DELETE FROM federated_audit_events WHERE sequence = ?",
            (second.sequence,),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(PermissionError, match="external_federated_audit_checkpoint_ahead_or_diverged"):
        FederatedAuditSynchronizer(
            log, anchor, namespace="noryx7/federation-a"
        ).synchronize()
    assert first.sequence < second.sequence


def test_federated_audit_external_anchor_fails_closed_on_outage(tmp_path):
    class Broken:
        def read_checkpoint(self, namespace):
            raise OSError("offline")
        def compare_and_advance(self, namespace, expected, next_checkpoint):
            raise OSError("offline")

    log = _log(tmp_path / "federated-anchor-offline.db")
    sync = FederatedAuditSynchronizer(
        log, Broken(), namespace="noryx7/federation-a"
    )
    with pytest.raises(PermissionError, match="external_federated_audit_anchor_unavailable"):
        sync.synchronize()



def test_anchored_sink_advances_external_checkpoint_for_every_record(tmp_path):
    log = _log(tmp_path / "automatic-anchor.db")
    anchor = FakeAnchor(log.checkpoint())
    sync = FederatedAuditSynchronizer(log, anchor, namespace="noryx7/federation-a")
    sink = AnchoredFederatedAuditSink(
        log, sync, SQLiteFederatedAuditWriterLease(tmp_path / "automatic-anchor.lease")
    )

    first = sink.record("decision", allowed=True)
    assert first["event"] == "decision"
    assert anchor.checkpoint.sequence == 1
    second = sink.record("outcome", outcome="dispatched")
    assert second["event"] == "outcome"
    assert anchor.checkpoint.sequence == 2
    assert log.checkpoint() == anchor.checkpoint


def test_anchored_sink_recovers_interrupted_commit_before_next_write(tmp_path):
    class FailFirstAdvance(FakeAnchor):
        def __init__(self, checkpoint):
            super().__init__(checkpoint)
            self.fail = True

        def compare_and_advance(self, namespace, expected, next_checkpoint):
            if self.fail:
                self.fail = False
                raise OSError("temporary anchor outage")
            return super().compare_and_advance(namespace, expected, next_checkpoint)

    log = _log(tmp_path / "automatic-anchor-recovery.db")
    anchor = FailFirstAdvance(log.checkpoint())
    sync = FederatedAuditSynchronizer(log, anchor, namespace="noryx7/federation-a")
    sink = AnchoredFederatedAuditSink(
        log, sync, SQLiteFederatedAuditWriterLease(tmp_path / "automatic-anchor.lease")
    )

    with pytest.raises(PermissionError, match="external_federated_audit_anchor_unavailable"):
        sink.record("decision", allowed=True)
    assert len(log.snapshot()) == 1
    assert anchor.checkpoint.sequence == 0

    # The next call reconciles the already committed row before appending.
    sink.record("outcome", outcome="dispatched")
    assert len(log.snapshot()) == 2
    assert anchor.checkpoint.sequence == 2
    assert log.checkpoint() == anchor.checkpoint


def test_anchored_sink_does_not_append_when_anchor_is_unavailable_before_write(tmp_path):
    class OfflineAnchor:
        def read_checkpoint(self, namespace):
            raise OSError("offline")
        def compare_and_advance(self, namespace, expected, next_checkpoint):
            raise OSError("offline")

    log = _log(tmp_path / "automatic-anchor-offline.db")
    sync = FederatedAuditSynchronizer(
        log, OfflineAnchor(), namespace="noryx7/federation-a"
    )
    sink = AnchoredFederatedAuditSink(
        log, sync, SQLiteFederatedAuditWriterLease(tmp_path / "offline-anchor.lease")
    )
    with pytest.raises(PermissionError, match="external_federated_audit_anchor_unavailable"):
        sink.record("decision", allowed=True)
    assert log.snapshot() == ()



def test_anchored_sink_serializes_independent_process_writers(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    database = tmp_path / "shared-audit.sqlite"
    lease_database = tmp_path / "shared-audit-writer.lease"
    first_log = _log(database)
    anchor = FakeAnchor(first_log.checkpoint())
    first_sync = FederatedAuditSynchronizer(
        first_log, anchor, namespace="noryx7/federation-shared"
    )
    first_sink = AnchoredFederatedAuditSink(
        first_log, first_sync, SQLiteFederatedAuditWriterLease(lease_database)
    )

    second_log = _log(database)
    second_sync = FederatedAuditSynchronizer(
        second_log, anchor, namespace="noryx7/federation-shared"
    )
    second_sink = AnchoredFederatedAuditSink(
        second_log, second_sync, SQLiteFederatedAuditWriterLease(lease_database)
    )

    sinks = (first_sink, second_sink)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda index: sinks[index % 2].record("parallel", writer=index),
            range(32),
        ))

    assert len(results) == 32
    assert len(first_log.snapshot()) == 32
    assert first_log.checkpoint() == anchor.checkpoint
    assert anchor.checkpoint.sequence == 32
    second_log.close()
    first_log.close()



def test_writer_lease_rejects_invalid_paths_and_timeouts(tmp_path):
    with pytest.raises(ValueError, match="durable_audit_writer_lease_required"):
        SQLiteFederatedAuditWriterLease(":memory:")
    with pytest.raises(ValueError, match="durable_audit_writer_lease_required"):
        SQLiteFederatedAuditWriterLease(" ")
    for timeout in (True, 0, -1, float("nan"), float("inf"), 301):
        with pytest.raises(ValueError, match="invalid_audit_writer_lease_timeout"):
            SQLiteFederatedAuditWriterLease(tmp_path / "invalid.lease", timeout=timeout)


def test_anchored_sink_rejects_synchronizer_for_different_audit_log(tmp_path):
    first = _log(tmp_path / "first.sqlite")
    second = _log(tmp_path / "second.sqlite")
    anchor = FakeAnchor(first.checkpoint())
    sync = FederatedAuditSynchronizer(
        first, anchor, namespace="noryx7/federation-mismatch"
    )
    with pytest.raises(ValueError, match="federated_audit_synchronizer_log_mismatch"):
        AnchoredFederatedAuditSink(
            second, sync, SQLiteFederatedAuditWriterLease(tmp_path / "mismatch.lease")
        )
    first.close()
    second.close()



class SQLiteFakeAnchor:
    """Process-safe test anchor with atomic compare-and-advance semantics."""

    def __init__(self, database, namespace, genesis):
        self._database = str(database)
        self._namespace = namespace
        connection = sqlite3.connect(self._database, timeout=10)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS checkpoints ("
                "namespace TEXT PRIMARY KEY, sequence INTEGER NOT NULL, digest BLOB NOT NULL)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO checkpoints(namespace, sequence, digest) VALUES (?, ?, ?)",
                (namespace, genesis.sequence, genesis.digest),
            )
            connection.commit()
        finally:
            connection.close()

    def read_checkpoint(self, namespace):
        connection = sqlite3.connect(self._database, timeout=10)
        try:
            row = connection.execute(
                "SELECT sequence, digest FROM checkpoints WHERE namespace = ?",
                (namespace,),
            ).fetchone()
            if row is None:
                return None
            return FederatedAuditCheckpoint(int(row[0]), bytes(row[1]))
        finally:
            connection.close()

    def compare_and_advance(self, namespace, expected, next_checkpoint):
        connection = sqlite3.connect(self._database, timeout=10, isolation_level=None)
        try:
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT sequence, digest FROM checkpoints WHERE namespace = ?",
                (namespace,),
            ).fetchone()
            current = (
                None if row is None
                else FederatedAuditCheckpoint(int(row[0]), bytes(row[1]))
            )
            if current != expected:
                connection.execute("ROLLBACK")
                return False
            connection.execute(
                "UPDATE checkpoints SET sequence = ?, digest = ? WHERE namespace = ?",
                (next_checkpoint.sequence, next_checkpoint.digest, namespace),
            )
            connection.execute("COMMIT")
            return True
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


def _multiprocess_anchored_audit_writer(audit_db, lease_db, anchor_db, writer_id, count):
    log = SQLiteFederatedAuditLog(audit_db)
    anchor = SQLiteFakeAnchor(
        anchor_db, "noryx7/multiprocess-e2e", log.checkpoint_at(0)
    )
    synchronizer = FederatedAuditSynchronizer(
        log, anchor, namespace="noryx7/multiprocess-e2e"
    )
    sink = AnchoredFederatedAuditSink(
        log, synchronizer, SQLiteFederatedAuditWriterLease(lease_db, timeout=15)
    )
    try:
        for index in range(count):
            sink.record("multiprocess", writer=writer_id, index=index)
    finally:
        log.close()


def test_anchored_sink_serializes_real_independent_processes(tmp_path):
    import multiprocessing

    audit_db = tmp_path / "multiprocess-audit.sqlite"
    lease_db = tmp_path / "multiprocess-audit.lease"
    anchor_db = tmp_path / "multiprocess-anchor.sqlite"
    initial_log = SQLiteFederatedAuditLog(audit_db)
    genesis = initial_log.checkpoint_at(0)
    initial_log.close()
    SQLiteFakeAnchor(anchor_db, "noryx7/multiprocess-e2e", genesis)

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_multiprocess_anchored_audit_writer,
            args=(str(audit_db), str(lease_db), str(anchor_db), writer, 8),
        )
        for writer in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(40)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail("multiprocess_audit_writer_timed_out")
        assert process.exitcode == 0

    final_log = SQLiteFederatedAuditLog(audit_db)
    try:
        events = final_log.snapshot()
        local_head = final_log.checkpoint()
        external_head = SQLiteFakeAnchor(
            anchor_db, "noryx7/multiprocess-e2e", genesis
        ).read_checkpoint("noryx7/multiprocess-e2e")
        assert len(events) == 16
        assert {event["writer"] for event in events} == {0, 1}
        assert local_head.sequence == 16
        assert local_head == external_head
        assert final_log.verify_integrity()
    finally:
        final_log.close()
