import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.sqlite_federated_audit import SQLiteFederatedAuditLog


def test_sqlite_audit_survives_restart_and_verifies_hash_chain(tmp_path):
    path = tmp_path / "federated-audit.sqlite"
    first = SQLiteFederatedAuditLog(path, clock=lambda: 100.0)
    first.record("federated_action_decision", principal_id="p-1", action_id="a-1")
    first.record("federated_action_outcome", principal_id="p-1", outcome="dispatched")
    digest = first.digest()
    assert first.verify_integrity()
    first.close()

    second = SQLiteFederatedAuditLog(path, clock=lambda: 101.0)
    assert second.verify_integrity()
    assert second.digest() == digest
    assert [row["event"] for row in second.snapshot()] == [
        "federated_action_decision", "federated_action_outcome"
    ]
    second.record("federated_action_outcome", principal_id="p-2", outcome="executor_failed")
    assert len(second.snapshot()) == 3
    second.close()


def test_sqlite_audit_rejects_mutation_and_detects_out_of_band_corruption(tmp_path):
    path = tmp_path / "federated-audit.sqlite"
    audit = SQLiteFederatedAuditLog(path)
    audit.record("federated_action_decision", principal_id="p-1")
    with pytest.raises(sqlite3.IntegrityError, match="federated_audit_append_only"):
        audit._conn.execute(
            "UPDATE federated_audit_events SET event_json='{}' WHERE sequence=1"
        )
    audit.close()

    tamper = sqlite3.connect(path)
    tamper.execute("DROP TRIGGER federated_audit_no_update")
    tamper.execute(
        "UPDATE federated_audit_events SET event_json='{}' WHERE sequence=1"
    )
    tamper.commit()
    tamper.close()
    with pytest.raises(RuntimeError, match="federated_audit_integrity_failed"):
        SQLiteFederatedAuditLog(path)


def test_sqlite_audit_serializes_concurrent_appends_without_sequence_gaps(tmp_path):
    audit = SQLiteFederatedAuditLog(tmp_path / "concurrent.sqlite")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: audit.record("worker_event", worker=n), range(40)))
    snapshot = audit.snapshot()
    assert len(snapshot) == 40
    assert audit.verify_integrity()
    assert len({row["worker"] for row in snapshot}) == 40
    audit.close()


def test_sqlite_audit_requires_a_file_backed_database_and_valid_clock(tmp_path):
    with pytest.raises(ValueError, match="durable_audit_database_required"):
        SQLiteFederatedAuditLog(":memory:")
    audit = SQLiteFederatedAuditLog(tmp_path / "invalid-clock.sqlite", clock=lambda: float("nan"))
    with pytest.raises(RuntimeError, match="audit_clock_invalid"):
        audit.record("test")
    assert audit.snapshot() == ()
    audit.close()


def test_sqlite_audit_bounds_record_size_and_rejects_unrepresentable_clock(tmp_path):
    audit = SQLiteFederatedAuditLog(tmp_path / "bounded.sqlite")
    with pytest.raises(ValueError, match="audit_record_too_large"):
        audit.record("oversized", payload="x" * 70_000)
    audit.close()

    huge_clock = SQLiteFederatedAuditLog(
        tmp_path / "huge-clock.sqlite", clock=lambda: 10 ** 10000
    )
    with pytest.raises(RuntimeError, match="audit_clock_invalid"):
        huge_clock.record("clock_overflow")
    assert huge_clock.snapshot() == ()
    huge_clock.close()


def test_checkpoint_is_verified_before_external_anchor_can_observe_it(tmp_path):
    path = tmp_path / "checkpoint.sqlite"
    audit = SQLiteFederatedAuditLog(path)
    audit.record("federated_action_outcome", outcome="dispatched")
    sequence, digest = audit.checkpoint()
    assert sequence == 1
    assert digest == audit.digest()

    tamper = sqlite3.connect(path)
    tamper.execute("DROP TRIGGER federated_audit_no_update")
    tamper.execute(
        "UPDATE federated_audit_events SET event_json='{}' WHERE sequence=1"
    )
    tamper.commit()
    tamper.close()

    assert audit.verify_integrity() is False
    with pytest.raises(RuntimeError, match="federated_audit_integrity_failed"):
        audit.checkpoint()
    with pytest.raises(RuntimeError, match="federated_audit_integrity_failed"):
        audit.digest()
    audit.close()


def test_empty_checkpoint_uses_genesis_and_zero_sequence(tmp_path):
    audit = SQLiteFederatedAuditLog(tmp_path / "empty-checkpoint.sqlite")
    sequence, digest = audit.checkpoint()
    assert sequence == 0
    assert digest == audit.digest()
    audit.close()


def test_independent_audit_connections_serialize_concurrent_process_style_appends(tmp_path):
    path = tmp_path / "independent-writers.sqlite"
    first = SQLiteFederatedAuditLog(path)
    second = SQLiteFederatedAuditLog(path)
    writers = (first, second)
    try:
        def append(index):
            return writers[index % 2].record("independent_writer", worker=index)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(append, range(48)))

        assert len(first.snapshot()) == 48
        assert first.verify_integrity()
        assert second.verify_integrity()
        sequence, digest = first.checkpoint()
        assert sequence == 48
        assert digest == second.checkpoint()[1]
    finally:
        first.close()
        second.close()


def test_external_anchor_comparison_detects_rollback_and_divergence(tmp_path):
    audit = SQLiteFederatedAuditLog(tmp_path / "anchor-check.sqlite")
    audit.record("event", value=1)
    sequence, digest = audit.checkpoint()
    assert audit.verify_against_anchor(sequence, digest) == (sequence, digest)

    with pytest.raises(RuntimeError, match="federated_audit_rollback_detected"):
        audit.verify_against_anchor(sequence + 1, digest)
    with pytest.raises(RuntimeError, match="federated_audit_anchor_divergence"):
        audit.verify_against_anchor(sequence, "0" * 64)
    with pytest.raises(ValueError, match="invalid_external_audit_checkpoint_sequence"):
        audit.verify_against_anchor(True, digest)
    with pytest.raises(ValueError, match="invalid_external_audit_checkpoint_digest"):
        audit.verify_against_anchor(sequence, "not-a-digest")

    # A locally newer journal is not rolled back; caller receives the newer
    # checkpoint and must advance the independent anchor before claiming sync.
    audit.record("event", value=2)
    newer = audit.verify_against_anchor(sequence, digest)
    assert newer[0] == sequence + 1
    audit.close()



def test_checkpoint_verification_and_head_share_one_sqlite_read_snapshot(tmp_path):
    path = tmp_path / "stable-checkpoint-snapshot.sqlite"
    reader = SQLiteFederatedAuditLog(path, clock=lambda: 10.0)
    writer = SQLiteFederatedAuditLog(path, clock=lambda: 11.0)
    try:
        reader.record("event", value="verified-prefix")
        original_verify = reader._verify_locked
        injected = {"done": False}

        def verify_then_concurrent_append():
            valid = original_verify()
            if valid and not injected["done"]:
                injected["done"] = True
                writer.record("event", value="concurrent-append")
            return valid

        reader._verify_locked = verify_then_concurrent_append
        sequence, digest = reader.checkpoint()

        # The append committed after the reader established its snapshot.
        # It must not leak into a checkpoint whose verification predates it.
        assert (sequence, digest) == (1, reader._event_digest(
            reader._conn.execute(
                "SELECT previous_digest FROM federated_audit_events WHERE sequence=1"
            ).fetchone()[0],
            reader._conn.execute(
                "SELECT event_json FROM federated_audit_events WHERE sequence=1"
            ).fetchone()[0],
        ))
        assert writer.checkpoint()[0] == 2
        assert reader.checkpoint()[0] == 2
    finally:
        reader.close()
        writer.close()


def test_external_anchor_sync_advances_monotonically_with_compare_and_swap(tmp_path):
    import hashlib

    class MemoryAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()

        def read_checkpoint(self):
            return self.sequence, self.digest

        def compare_and_advance(self, expected_sequence, expected_digest,
                                next_sequence, next_digest):
            if (self.sequence, self.digest) != (expected_sequence, expected_digest):
                return False
            if next_sequence <= expected_sequence:
                return False
            self.sequence, self.digest = next_sequence, next_digest
            return True

    audit = SQLiteFederatedAuditLog(tmp_path / "anchor-sync.sqlite")
    anchor = MemoryAnchor()
    audit.record("event", value="first")
    checkpoint = audit.synchronize_external_anchor(anchor)
    assert checkpoint == anchor.read_checkpoint()
    assert audit.synchronize_external_anchor(anchor) == checkpoint
    audit.close()


def test_external_anchor_sync_fails_closed_on_conflict_or_unavailable_service(tmp_path):
    import hashlib

    genesis = hashlib.sha256(
        b"noryx7/sqlite-federated-audit/genesis/v1"
    ).hexdigest()

    class ConflictingAnchor:
        def read_checkpoint(self):
            return 0, genesis

        def compare_and_advance(self, *_args):
            return False

    class UnavailableAnchor:
        def read_checkpoint(self):
            raise OSError("anchor offline")

        def compare_and_advance(self, *_args):
            return False

    audit = SQLiteFederatedAuditLog(tmp_path / "anchor-fail-closed.sqlite")
    audit.record("event", value="pending")
    with pytest.raises(RuntimeError, match="external_audit_anchor_advance_conflict"):
        audit.synchronize_external_anchor(ConflictingAnchor())
    with pytest.raises(RuntimeError, match="external_audit_anchor_unavailable"):
        audit.synchronize_external_anchor(UnavailableAnchor())
    audit.close()


def test_external_anchor_sync_is_idempotent_across_concurrent_audit_instances(tmp_path):
    import hashlib
    from threading import Lock

    genesis = hashlib.sha256(
        b"noryx7/sqlite-federated-audit/genesis/v1"
    ).hexdigest()

    class ConcurrentAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = genesis
            self.lock = Lock()

        def read_checkpoint(self):
            with self.lock:
                return self.sequence, self.digest

        def compare_and_advance(
            self, expected_sequence, expected_digest, next_sequence, next_digest
        ):
            with self.lock:
                if (self.sequence, self.digest) != (expected_sequence, expected_digest):
                    return False
                if next_sequence <= expected_sequence:
                    return False
                self.sequence, self.digest = next_sequence, next_digest
                return True

    path = tmp_path / "concurrent-anchor-sync.sqlite"
    first = SQLiteFederatedAuditLog(path)
    second = SQLiteFederatedAuditLog(path)
    anchor = ConcurrentAnchor()
    try:
        first.record("event", value="shared-prefix")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda audit: audit.synchronize_external_anchor(anchor),
                (first, second),
            ))
        assert results[0] == results[1] == anchor.read_checkpoint()
        assert first.checkpoint() == second.checkpoint() == results[0]
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("checkpoint", [
    None,
    [0, "0" * 64],
    (True, "0" * 64),
    (-1, "0" * 64),
    (0, "not-a-digest"),
    (0, "A" * 64),
])
def test_external_anchor_sync_rejects_malformed_checkpoint_values(tmp_path, checkpoint):
    class MalformedAnchor:
        def read_checkpoint(self):
            return checkpoint

        def compare_and_advance(self, *_args):
            raise AssertionError("must not advance an invalid anchor")

    audit = SQLiteFederatedAuditLog(tmp_path / "malformed-anchor.sqlite")
    audit.record("event", value="pending")
    with pytest.raises(RuntimeError, match="external_audit_anchor_invalid_checkpoint"):
        audit.synchronize_external_anchor(MalformedAnchor())
    assert audit.checkpoint()[0] == 1
    audit.close()
