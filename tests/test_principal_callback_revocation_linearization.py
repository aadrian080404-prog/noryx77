from concurrent.futures import ThreadPoolExecutor
from threading import Event

from core.principal_identity import PrincipalIdentityAuthority
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def test_revocation_waits_for_inflight_trusted_principal_callback(tmp_path):
    database = tmp_path / "callback-revocation-linearization.sqlite3"
    identity, _private_key = PrincipalIdentityAuthority.generate("tenant:linearized")
    callback_registry = SQLitePrincipalIdentityRegistry(database)
    revocation_registry = SQLitePrincipalIdentityRegistry(database)
    callback_registry.register(identity)

    callback_entered = Event()
    release_callback = Event()
    revocation_started = Event()

    def trusted_callback(current):
        callback_entered.set()
        assert release_callback.wait(timeout=5)
        return current.principal_id

    def revoke_after_callback_starts():
        revocation_started.set()
        revocation_registry.revoke(identity.principal_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        callback_future = pool.submit(
            callback_registry.with_trusted_principal,
            identity.principal_id,
            trusted_callback,
        )
        assert callback_entered.wait(timeout=5)
        revoke_future = pool.submit(revoke_after_callback_starts)
        assert revocation_started.wait(timeout=5)
        release_callback.set()

        assert callback_future.result(timeout=10) == identity.principal_id
        revoke_future.result(timeout=10)

    assert callback_registry.is_revoked(identity.principal_id) is True
    assert callback_registry.is_registered(identity.principal_id) is False
    assert callback_registry.is_trusted(identity) is False
