import sqlite3

import pytest

from core.federated_audit_anchor import (
    AnchoredFederatedAuditSink,
    FederatedAuditCheckpoint,
    FederatedAuditSynchronizer,
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
    sink = AnchoredFederatedAuditSink(log, sync)

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
    sink = AnchoredFederatedAuditSink(log, sync)

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
    sink = AnchoredFederatedAuditSink(log, sync)
    with pytest.raises(PermissionError, match="external_federated_audit_anchor_unavailable"):
        sink.record("decision", allowed=True)
    assert log.snapshot() == ()
