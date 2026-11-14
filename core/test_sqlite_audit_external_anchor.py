import os
import sqlite3

import pytest

from core.journal_integrity import AnchorSnapshot, InMemoryMonotonicAnchor, ZERO_MAC
from core.sqlite_audit import SQLiteAuditLog


def backup_database(source_path, destination_path):
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def test_external_anchor_detects_restored_older_database(tmp_path):
    path = str(tmp_path / "audit.sqlite")
    old_copy = str(tmp_path / "old-audit.sqlite")
    anchor = InMemoryMonotonicAnchor()
    audit = SQLiteAuditLog(path)
    audit.record("first")
    first_head = audit.verify_and_advance_anchor(anchor)
    backup_database(path, old_copy)

    audit.record("second")
    second_head = audit.verify_and_advance_anchor(anchor)
    assert second_head.sequence == first_head.sequence + 1
    audit.close()

    # Restore a complete SQLite snapshot, not just the main database file.
    # A stale WAL/SHM sidecar from the newer database can otherwise be replayed
    # over the restored file and make the fixture test the wrong failure mode.
    for suffix in ("-wal", "-shm"):
        sidecar = path + suffix
        if os.path.exists(sidecar):
            os.remove(sidecar)
    os.replace(old_copy, path)
    restored = SQLiteAuditLog(path)
    with pytest.raises(ValueError, match="audit_database_rollback_detected"):
        restored.verify_and_advance_anchor(anchor)
    restored.close()


def test_external_anchor_recovers_valid_unanchored_tail_after_crash(tmp_path):
    path = str(tmp_path / "audit.sqlite")
    anchor = InMemoryMonotonicAnchor()
    audit = SQLiteAuditLog(path)
    audit.record("anchored")
    first = audit.verify_and_advance_anchor(anchor)
    audit.record("local-append-before-crash-1")
    audit.record("local-append-before-crash-2")
    audit.close()

    reopened = SQLiteAuditLog(path)
    recovered = reopened.verify_and_advance_anchor(anchor)
    assert recovered.sequence == first.sequence + 2
    assert anchor.read() == recovered
    assert reopened.verify_integrity()
    reopened.close()


def test_external_anchor_rejects_same_sequence_divergent_chain(tmp_path):
    path = str(tmp_path / "audit.sqlite")
    anchor = InMemoryMonotonicAnchor()
    audit = SQLiteAuditLog(path)
    audit.record("original")
    audit.verify_and_advance_anchor(anchor)
    audit.close()

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE audit_events SET event_json=? WHERE sequence=1",
            ('{"event":"substituted"}',),
        )
    tampered = SQLiteAuditLog(path)
    with pytest.raises(ValueError, match="audit_integrity_failed"):
        tampered.verify_and_advance_anchor(anchor)
    tampered.close()

def test_external_anchor_rejects_noncanonical_sha256_encoding(tmp_path):
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


def test_external_anchor_recovers_cas_commit_when_remote_reply_is_lost(tmp_path):
    class CommitThenLoseReply:
        def __init__(self):
            self.inner = InMemoryMonotonicAnchor()
            self.lose_once = True

        def read(self):
            return self.inner.read()

        def compare_and_swap(self, expected, replacement):
            accepted = self.inner.compare_and_swap(expected, replacement)
            if accepted and self.lose_once:
                self.lose_once = False
                raise OSError("simulated_lost_remote_reply")
            return accepted

    audit = SQLiteAuditLog(str(tmp_path / "uncertain-anchor.sqlite"))
    anchor = CommitThenLoseReply()
    try:
        audit.record("one")
        audit.record("two")
        head = audit.verify_and_advance_anchor(anchor)
        assert head.sequence == 2
        assert anchor.read() == head
        assert audit.verify_integrity()
    finally:
        audit.close()
