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
