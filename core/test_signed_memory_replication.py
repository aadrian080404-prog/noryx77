import pytest

from core.distributed_memory import DistributedMemoryStore
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.signed_memory_replication import (
    SignedMemoryBatch,
    sign_memory_batch,
    verify_and_merge_memory_batch,
)


def test_signed_batch_authenticates_sender_and_merges_idempotently(tmp_path):
    identity, private = AgentIdentityAuthority.generate("node-a")
    registry = IdentityRegistry()
    registry.register(identity)
    source = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="node-a")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="node-b")
    source.write("k", "v")
    batch = sign_memory_batch(identity, private, source.export_since({}))
    assert verify_and_merge_memory_batch(target, batch, registry) == 1
    assert verify_and_merge_memory_batch(target, batch, registry) == 0
    assert target.read("k").value == "v"
    source.close()
    target.close()


def test_untrusted_sender_is_rejected(tmp_path):
    identity, private = AgentIdentityAuthority.generate("node-a")
    registry = IdentityRegistry()
    source = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="node-a")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="node-b")
    source.write("k", "v")
    batch = sign_memory_batch(identity, private, source.export_since({}))
    with pytest.raises(PermissionError, match="not_trusted"):
        verify_and_merge_memory_batch(target, batch, registry)
    assert target.read("k") is None
    source.close()
    target.close()


def test_tampered_batch_and_sender_actor_mismatch_are_rejected(tmp_path):
    identity, private = AgentIdentityAuthority.generate("node-a")
    registry = IdentityRegistry()
    registry.register(identity)
    source = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="node-a")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="node-b")
    source.write("k", "original")
    batch = sign_memory_batch(identity, private, source.export_since({}))
    altered_event = type(batch.events[0])(
        batch.events[0].actor_id, batch.events[0].counter, "k", "tampered",
        False, batch.events[0].clock
    )
    tampered = SignedMemoryBatch(batch.attestation, (altered_event,))
    with pytest.raises(PermissionError, match="statement_mismatch"):
        verify_and_merge_memory_batch(target, tampered, registry)
    with pytest.raises(ValueError, match="actor_identity_mismatch"):
        sign_memory_batch(identity, private, (
            type(batch.events[0])("other-node", 1, "x", "v", False, (("other-node", 1),)),
        ))
    assert target.read("k") is None
    source.close()
    target.close()


def test_revoked_sender_cannot_replay_old_signed_batch(tmp_path):
    identity, private = AgentIdentityAuthority.generate("node-a")
    registry = IdentityRegistry()
    registry.register(identity)
    source = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="node-a")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="node-b")
    source.write("k", "v")
    batch = sign_memory_batch(identity, private, source.export_since({}))
    registry.revoke("node-a")
    with pytest.raises(PermissionError, match="not_trusted"):
        verify_and_merge_memory_batch(target, batch, registry)
    source.close()
    target.close()
