import hashlib

import pytest

from core.principal_identity import (
    PrincipalIdentity,
    PrincipalIdentityAuthority,
    PrincipalIdentityRegistry,
)
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def test_principal_proof_binds_id_key_and_statement():
    identity, private_key = PrincipalIdentityAuthority.generate("user:001")
    proof = PrincipalIdentityAuthority.prove(identity, private_key, b"enrollment-v1")

    assert PrincipalIdentityAuthority.verify(proof) is True
    assert PrincipalIdentityAuthority.verify(
        type(proof)(identity, b"changed-statement", proof.signature)
    ) is False


def test_principal_proof_rejects_wrong_private_key():
    identity, _private_key = PrincipalIdentityAuthority.generate("user:002")
    _other_identity, other_private_key = PrincipalIdentityAuthority.generate("user:other")

    with pytest.raises(ValueError, match="principal_private_key_mismatch"):
        PrincipalIdentityAuthority.prove(identity, other_private_key, b"enrollment")


def test_principal_identity_validates_fields():
    with pytest.raises(ValueError, match="invalid_principal_identity"):
        PrincipalIdentityRegistry().register(PrincipalIdentity(" ", b"x" * 32))


def test_sqlite_principal_trust_survives_restart_and_revocation_is_permanent(tmp_path):
    database = tmp_path / "principal-trust.sqlite3"
    identity, _private_key = PrincipalIdentityAuthority.generate("tenant:alpha")

    first = SQLitePrincipalIdentityRegistry(database)
    first.register(identity)
    assert first.is_trusted(identity) is True
    assert first.is_registered(identity.principal_id) is True
    assert first.is_revoked(identity.principal_id) is False
    first.revoke(identity.principal_id)

    reopened = SQLitePrincipalIdentityRegistry(database)
    assert reopened.is_trusted(identity) is False
    assert reopened.is_registered(identity.principal_id) is False
    assert reopened.is_revoked(identity.principal_id) is True
    with pytest.raises(PermissionError, match="permanently_revoked"):
        reopened.register(identity)
    with pytest.raises(PermissionError, match="permanently_revoked"):
        reopened.with_trusted_principal(identity.principal_id, lambda current: current)


def test_sqlite_registry_rejects_duplicate_and_key_replacement(tmp_path):
    database = tmp_path / "principal-duplicate.sqlite3"
    identity, _private_key = PrincipalIdentityAuthority.generate("tenant:beta")
    replacement, _replacement_key = PrincipalIdentityAuthority.generate("tenant:beta")

    registry = SQLitePrincipalIdentityRegistry(database)
    registry.register(identity)
    with pytest.raises(ValueError, match="already_registered"):
        registry.register(identity)
    assert registry.is_trusted(replacement) is False


def test_sqlite_with_trusted_principal_runs_against_current_durable_key(tmp_path):
    database = tmp_path / "principal-callback.sqlite3"
    identity, _private_key = PrincipalIdentityAuthority.generate("tenant:gamma")
    registry = SQLitePrincipalIdentityRegistry(database)
    registry.register(identity)

    fingerprint = registry.with_trusted_principal(
        identity.principal_id,
        lambda current: hashlib.sha256(current.public_key).hexdigest(),
    )
    assert fingerprint == hashlib.sha256(identity.public_key).hexdigest()


def test_sqlite_registry_fails_closed_for_invalid_principal_lookup(tmp_path):
    registry = SQLitePrincipalIdentityRegistry(tmp_path / "principal-invalid.sqlite3")
    assert registry.is_revoked("") is True
    assert registry.is_trusted(PrincipalIdentity("missing", b"x" * 32)) is False


def test_in_memory_registry_also_keeps_revocation_tombstones():
    identity, _private_key = PrincipalIdentityAuthority.generate("user:memory")
    registry = PrincipalIdentityRegistry()
    registry.register(identity)
    assert registry.is_trusted(identity)
    registry.revoke(identity.principal_id)
    assert registry.is_revoked(identity.principal_id)
    with pytest.raises(PermissionError, match="permanently_revoked"):
        registry.register(identity)
