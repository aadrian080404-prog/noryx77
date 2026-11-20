import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.sqlite_federated_audit import (
    SQLiteExternalAuditAnchor,
    SQLiteFederatedAuditLog,
)


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


def test_external_anchor_rejects_malformed_checkpoint_shapes_and_values(tmp_path):
    class MalformedAnchor:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        def read_checkpoint(self):
            return self.checkpoint

        def compare_and_advance(self, *_args):
            raise AssertionError("must_not_advance_malformed_checkpoint")

    audit = SQLiteFederatedAuditLog(tmp_path / "malformed-external-anchor.sqlite")
    audit.record("anchored-prefix")
    audit.record("unanchored-tail")
    for checkpoint in (
        None,
        [0, "0" * 64],
        (True, "0" * 64),
        (-1, "0" * 64),
        (0, "A" * 64),
        (0, "0" * 64),
        (1, "0" * 64),
        (0, "not-a-digest"),
    ):
        with pytest.raises((RuntimeError, ValueError)):
            audit.synchronize_external_anchor(MalformedAnchor(checkpoint))
    audit.close()


def test_external_anchor_rejects_false_success_without_confirmed_advance(tmp_path):
    class LyingAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()

        def read_checkpoint(self):
            return self.sequence, self.digest

        def compare_and_advance(self, *_args):
            return True

    audit = SQLiteFederatedAuditLog(tmp_path / "lying-external-anchor.sqlite")
    audit.record("pending")
    with pytest.raises(
        RuntimeError, match="external_audit_anchor_confirmation_mismatch"
    ):
        audit.synchronize_external_anchor(LyingAnchor())
    assert audit.verify_integrity()
    audit.close()


def test_external_anchor_rejects_non_boolean_compare_and_advance_result(tmp_path):
    class InvalidCASResultAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()

        def read_checkpoint(self):
            return self.sequence, self.digest

        def compare_and_advance(self, *_args):
            return 1

    audit = SQLiteFederatedAuditLog(tmp_path / "invalid-cas-result.sqlite")
    audit.record("pending")
    with pytest.raises(RuntimeError, match="external_audit_anchor_advance_conflict"):
        audit.synchronize_external_anchor(InvalidCASResultAnchor())
    assert audit.verify_integrity()
    audit.close()

def test_historical_anchor_prefix_verifies_after_restart_with_unanchored_tail(tmp_path):
    path = tmp_path / "historical-anchor-restart.sqlite"
    first = SQLiteFederatedAuditLog(path)
    first.record("anchored-event", value="stable")
    anchor_sequence, anchor_digest = first.checkpoint()
    first.record("unanchored-tail", value="later")
    first.close()

    reopened = SQLiteFederatedAuditLog(path)
    try:
        local_sequence, local_digest = reopened.verify_against_anchor(
            anchor_sequence, anchor_digest
        )
        assert local_sequence == anchor_sequence + 1
        assert local_digest == reopened.checkpoint()[1]
        with pytest.raises(
            RuntimeError, match="federated_audit_anchor_divergence"
        ):
            reopened.verify_against_anchor(anchor_sequence, "0" * 64)
        assert reopened.verify_integrity()
    finally:
        reopened.close()

def test_independent_audit_clients_converge_on_concurrent_anchor_sync(tmp_path):
    from threading import Barrier, Lock

    class ThreadSafeAnchor:
        def __init__(self):
            self._lock = Lock()
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()

        def read_checkpoint(self):
            with self._lock:
                return self.sequence, self.digest

        def compare_and_advance(
            self, expected_sequence, expected_digest, next_sequence, next_digest
        ):
            with self._lock:
                if (self.sequence, self.digest) != (
                    expected_sequence, expected_digest
                ):
                    return False
                if next_sequence <= expected_sequence:
                    return False
                self.sequence, self.digest = next_sequence, next_digest
                return True

    path = tmp_path / "concurrent-anchor-sync.sqlite"
    first = SQLiteFederatedAuditLog(path)
    second = SQLiteFederatedAuditLog(path)
    first.record("event", value="shared-prefix")
    anchor = ThreadSafeAnchor()
    barrier = Barrier(2)
    try:
        def synchronize(audit):
            barrier.wait(timeout=10)
            return audit.synchronize_external_anchor(anchor)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(synchronize, (first, second)))

        assert results[0] == results[1]
        assert results[0] == anchor.read_checkpoint()
        assert results[0][0] == 1
        assert first.verify_integrity()
        assert second.verify_integrity()
    finally:
        first.close()
        second.close()



def test_external_anchor_sync_recovers_when_cas_acknowledgement_is_lost(tmp_path):
    class LostAcknowledgementAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()
            self.drop_first_acknowledgement = True

        def read_checkpoint(self):
            return self.sequence, self.digest

        def compare_and_advance(
            self, expected_sequence, expected_digest, next_sequence, next_digest
        ):
            if (self.sequence, self.digest) != (
                expected_sequence, expected_digest
            ):
                return False
            self.sequence, self.digest = next_sequence, next_digest
            if self.drop_first_acknowledgement:
                self.drop_first_acknowledgement = False
                return False
            return True

    audit = SQLiteFederatedAuditLog(tmp_path / "lost-anchor-ack.sqlite")
    audit.record("event", value="durable-before-anchor")
    anchor = LostAcknowledgementAnchor()
    try:
        # The CAS has committed remotely, but its acknowledgement was lost.
        # Re-reading the exact desired checkpoint must make retry idempotent.
        expected = audit.checkpoint()
        assert audit.synchronize_external_anchor(anchor) == expected
        assert anchor.read_checkpoint() == expected
        assert audit.synchronize_external_anchor(anchor) == expected
        assert audit.verify_integrity()
    finally:
        audit.close()


def test_external_anchor_sync_recovers_after_commit_then_timeout(tmp_path):
    class CommitThenTimeoutAnchor:
        def __init__(self):
            self.sequence = 0
            self.digest = hashlib.sha256(
                b"noryx7/sqlite-federated-audit/genesis/v1"
            ).hexdigest()
            self.applied = False

        def read_checkpoint(self):
            return self.sequence, self.digest

        def compare_and_advance(
            self, expected_sequence, expected_digest, next_sequence, next_digest
        ):
            if (self.sequence, self.digest) != (
                expected_sequence, expected_digest
            ):
                return False
            self.sequence, self.digest = next_sequence, next_digest
            if not self.applied:
                self.applied = True
                raise TimeoutError("response lost after durable commit")
            return True

    audit = SQLiteFederatedAuditLog(tmp_path / "anchor-timeout-after-commit.sqlite")
    audit.record("event", value="committed-once")
    anchor = CommitThenTimeoutAnchor()
    expected = audit.checkpoint()
    try:
        with pytest.raises(
            RuntimeError, match="external_audit_anchor_unavailable"
        ):
            audit.synchronize_external_anchor(anchor)
        assert anchor.read_checkpoint() == expected
        # Retry observes the already-committed checkpoint and does not append twice.
        assert audit.synchronize_external_anchor(anchor) == expected
        assert anchor.read_checkpoint() == expected
        assert audit.snapshot() == ({"event": "event", "value": "committed-once"},)
        assert audit.verify_integrity()
    finally:
        audit.close()


def test_sqlite_external_anchor_persists_and_advances_monotonically(tmp_path):
    journal = SQLiteFederatedAuditLog(tmp_path / "journal.sqlite")
    witness_path = tmp_path / "separate-witness.sqlite"
    witness = SQLiteExternalAuditAnchor(witness_path)
    journal.record("anchored", value="durable")
    expected = journal.checkpoint()
    try:
        assert witness.read_checkpoint()[0] == 0
        assert witness.compare_and_advance(0, hashlib.sha256(
            b"noryx7/sqlite-federated-audit/genesis/v1"
        ).hexdigest(), *expected) is True
        assert witness.read_checkpoint() == expected
        assert witness.compare_and_advance(0, hashlib.sha256(
            b"noryx7/sqlite-federated-audit/genesis/v1"
        ).hexdigest(), *expected) is False
    finally:
        journal.close()

    reopened = SQLiteExternalAuditAnchor(witness_path)
    assert reopened.read_checkpoint() == expected


def test_sqlite_external_anchor_rejects_invalid_or_non_monotonic_updates(tmp_path):
    anchor = SQLiteExternalAuditAnchor(tmp_path / "invalid-witness.sqlite")
    genesis = hashlib.sha256(
        b"noryx7/sqlite-federated-audit/genesis/v1"
    ).hexdigest()
    assert anchor.compare_and_advance(0, genesis, 0, "0" * 64) is False
    assert anchor.compare_and_advance(0, genesis, 1, "Z" * 64) is False
    assert anchor.read_checkpoint() == (0, genesis)


def test_sqlite_external_anchor_integrates_with_journal_sync(tmp_path):
    journal = SQLiteFederatedAuditLog(tmp_path / "journal-sync.sqlite")
    anchor = SQLiteExternalAuditAnchor(tmp_path / "independent-witness.sqlite")
    try:
        journal.record("federated_action", action_id="action-1")
        expected = journal.checkpoint()
        assert journal.synchronize_external_anchor(anchor) == expected
        assert anchor.read_checkpoint() == expected
        assert journal.synchronize_external_anchor(anchor) == expected
    finally:
        journal.close()
