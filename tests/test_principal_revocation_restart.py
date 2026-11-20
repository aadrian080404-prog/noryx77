import pytest

from core.principal_identity import PrincipalIdentity
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def test_revocation_tombstone_survives_restart_and_blocks_reregistration(tmp_path):
    path = tmp_path / "revoked-principal.sqlite"
    first = SQLitePrincipalIdentityRegistry(path)
    identity = PrincipalIdentity("tenant-revoked", b"k" * 32)
    first.register(identity)
    first.revoke(identity.principal_id)

    reopened = SQLitePrincipalIdentityRegistry(path)
    assert reopened.is_revoked(identity.principal_id) is True
    assert reopened.is_registered(identity.principal_id) is False
    assert reopened.is_trusted(identity) is False
    with pytest.raises(
        PermissionError, match="principal_identity_permanently_revoked"
    ):
        reopened.register(identity)
