import pytest
from .matrix_membership_durable import AdmissionEvidence, DurableMembershipRegistry, MemberState


def evidence(epoch=1, nonce="n-1", **kw):
    values = dict(node_id="node-1", owner_id="owner-1", failure_domain="region-a",
                  software_measurement="sha256:abc", epoch=epoch, nonce=nonce,
                  capabilities=frozenset({"compute", "verify"}))
    values.update(kw)
    return AdmissionEvidence(**values)


def verify(_evidence, proof):
    return proof == b"valid-proof"


def test_membership_survives_restart_and_revocation_tombstone(tmp_path):
    path = tmp_path / "membership.db"
    registry = DurableMembershipRegistry(path)
    active = registry.admit(evidence(), b"valid-proof", verify)
    assert active.state is MemberState.ACTIVE
    reopened = DurableMembershipRegistry(path)
    revoked = reopened.revoke("node-1", 2)
    assert revoked.state is MemberState.REVOKED and revoked.epoch == 2
    assert DurableMembershipRegistry(path).get("node-1") == revoked


def test_membership_rejects_replay_and_old_epoch_after_restart(tmp_path):
    path = tmp_path / "membership.db"
    registry = DurableMembershipRegistry(path)
    registry.admit(evidence(), b"valid-proof", verify)
    reopened = DurableMembershipRegistry(path)
    with pytest.raises(PermissionError, match="admission_nonce_replayed"):
        reopened.admit(evidence(), b"valid-proof", verify)
    with pytest.raises(PermissionError, match="membership_epoch_not_monotonic"):
        reopened.admit(evidence(epoch=1, nonce="new"), b"valid-proof", verify)


def test_membership_requires_newer_epoch_after_revocation(tmp_path):
    path = tmp_path / "membership.db"
    registry = DurableMembershipRegistry(path)
    registry.admit(evidence(), b"valid-proof", verify)
    registry.revoke("node-1", 4)
    with pytest.raises(PermissionError, match="membership_epoch_not_monotonic"):
        registry.admit(evidence(epoch=3, nonce="fresh"), b"valid-proof", verify)
    active = registry.admit(evidence(epoch=5, nonce="fresh-5"), b"valid-proof", verify)
    assert active.state is MemberState.ACTIVE and active.epoch == 5


def test_membership_owner_cannot_change_silently(tmp_path):
    registry = DurableMembershipRegistry(tmp_path / "membership.db")
    registry.admit(evidence(), b"valid-proof", verify)
    with pytest.raises(PermissionError, match="node_owner_change_requires_reenrollment"):
        registry.admit(evidence(epoch=2, nonce="n-2", owner_id="owner-2"), b"valid-proof", verify)
