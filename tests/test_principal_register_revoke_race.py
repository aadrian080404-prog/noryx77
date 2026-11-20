from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.principal_identity import PrincipalIdentity
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def test_concurrent_register_and_revoke_leave_irreversible_revocation(tmp_path):
    path = tmp_path / "principal-race.sqlite"
    first = SQLitePrincipalIdentityRegistry(path)
    second = SQLitePrincipalIdentityRegistry(path)
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    identity = PrincipalIdentity("tenant-race", public)
    barrier = Barrier(2)

    def register():
        barrier.wait(timeout=10)
        try:
            first.register(identity)
            return "registered"
        except PermissionError:
            return "revoked-first"

    def revoke():
        barrier.wait(timeout=10)
        second.revoke(identity.principal_id)
        return "revoked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda fn: fn(), (register, revoke)))

    assert "revoked" in outcomes
    assert first.is_revoked(identity.principal_id) is True
    assert first.is_registered(identity.principal_id) is False
    assert first.is_trusted(identity) is False
