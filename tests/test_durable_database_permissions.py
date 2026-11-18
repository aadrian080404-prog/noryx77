import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.sqlite_audit import SQLiteAuditLog
from core.sqlite_identity import SQLiteIdentityRegistry
from core.witness_authority import SQLiteWitnessAuthority


def _deny_chmod(*_args, **_kwargs):
    raise PermissionError("simulated_permission_failure")


def test_audit_database_permission_failure_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("core.sqlite_audit.os.chmod", _deny_chmod)
    with pytest.raises(RuntimeError, match="audit_database_permissions_unavailable"):
        SQLiteAuditLog(str(tmp_path / "audit.sqlite3"))


def test_identity_database_permission_failure_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("core.sqlite_identity.os.chmod", _deny_chmod)
    with pytest.raises(RuntimeError, match="identity_database_permissions_unavailable"):
        SQLiteIdentityRegistry(str(tmp_path / "identity.sqlite3"))


def test_witness_authority_requires_persistent_database():
    with pytest.raises(ValueError, match="persistent_witness_database_required"):
        SQLiteWitnessAuthority(
            ":memory:",
            witness_id="witness-memory",
            signing_key=Ed25519PrivateKey.generate(),
        )


def test_witness_database_permission_failure_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("core.witness_authority.os.chmod", _deny_chmod)
    with pytest.raises(RuntimeError, match="witness_database_permissions_unavailable"):
        SQLiteWitnessAuthority(
            str(tmp_path / "witness.sqlite3"),
            witness_id="witness-private",
            signing_key=Ed25519PrivateKey.generate(),
        )
