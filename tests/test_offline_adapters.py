import pytest

from core.crypto import AuthenticatedCipher, InMemoryKeyProvider, KEY_SIZE
from core.offline_adapters import BoundAuthenticatedCipher, PolicyOfflineAdapter
from core.policy import PolicyEngine


def test_policy_offline_adapter_binds_to_safe_compute_action():
    adapter = PolicyOfflineAdapter(PolicyEngine())
    assert adapter.authorize(principal_id="p1", operation="publish", offline=True) is True
    assert adapter.authorize(principal_id="p1", operation="", offline=True) is False
    assert adapter.authorize(principal_id="", operation="compute", offline=True) is False
    assert adapter.authorize(principal_id="p1", operation="compute", offline=False) is False


def test_bound_cipher_rejects_tampered_shape_and_aad():
    provider = InMemoryKeyProvider({"offline": b"K" * KEY_SIZE})
    bound = BoundAuthenticatedCipher(AuthenticatedCipher(provider), key_id="offline")
    aad = b"noryx7/offline-sync/v1/e1"
    blob = bound.encrypt(b"payload", aad=aad)
    assert bound.decrypt(blob, aad=aad) == b"payload"
    with pytest.raises(ValueError, match="offline_aad_mismatch"):
        bound.decrypt(blob, aad=b"wrong")
    with pytest.raises(ValueError):
        bound.decrypt(b"{}", aad=aad)
