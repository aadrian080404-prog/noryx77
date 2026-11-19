import pytest

from core.identity import (
    AgentIdentityAuthority,
    IdentityRegistry,
    identity_rotation_message,
)


def _rotation(agent_id="agent-rotation"):
    old_identity, old_private = AgentIdentityAuthority.generate(agent_id)
    new_identity, new_private = AgentIdentityAuthority.generate(agent_id)
    message = identity_rotation_message(
        agent_id, old_identity.public_key, new_identity.public_key, 1
    )
    return (
        old_identity,
        old_private,
        new_identity,
        old_private.sign(message),
        new_private.sign(message),
    )


def test_rotation_requires_both_old_and_new_key_proofs_and_advances_generation():
    old, _old_private, new, old_proof, new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)

    assert registry.generation(old.agent_id) == 1
    assert registry.rotate_identity(
        new,
        expected_generation=1,
        old_key_signature=old_proof,
        new_key_signature=new_proof,
    ) == 2
    assert registry.generation(old.agent_id) == 2
    assert not registry.is_trusted(old)
    assert registry.is_trusted(new)


def test_rotation_rejects_missing_or_invalid_old_key_proof():
    old, _old_private, new, _old_proof, new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)

    with pytest.raises(PermissionError, match="identity_rotation_proof_invalid"):
        registry.rotate_identity(
            new,
            expected_generation=1,
            old_key_signature=b"x" * 64,
            new_key_signature=new_proof,
        )
    assert registry.is_trusted(old)
    assert registry.generation(old.agent_id) == 1


def test_rotation_rejects_invalid_new_key_proof():
    old, _old_private, new, old_proof, _new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)

    with pytest.raises(PermissionError, match="identity_rotation_proof_invalid"):
        registry.rotate_identity(
            new,
            expected_generation=1,
            old_key_signature=old_proof,
            new_key_signature=b"x" * 64,
        )
    assert registry.is_trusted(old)


def test_rotation_compare_and_swap_rejects_stale_generation_and_replay():
    old, _old_private, new, old_proof, new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)
    registry.rotate_identity(
        new, expected_generation=1,
        old_key_signature=old_proof, new_key_signature=new_proof,
    )

    with pytest.raises(PermissionError, match="identity_generation_conflict"):
        registry.rotate_identity(
            new, expected_generation=1,
            old_key_signature=old_proof, new_key_signature=new_proof,
        )
    assert registry.generation(old.agent_id) == 2


def test_revoked_identity_is_a_tombstone_and_cannot_be_re_registered():
    old, _private, _new, _old_proof, _new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)
    registry.revoke(old.agent_id)

    with pytest.raises(PermissionError, match="agent_identity_permanently_revoked"):
        registry.register(old)
    with pytest.raises(PermissionError, match="agent_identity_not_active"):
        registry.generation(old.agent_id)


def test_rotation_generation_is_bounded_to_unsigned_64_bit_range():
    old, _old_private, new, _old_proof, _new_proof = _rotation()
    registry = IdentityRegistry()
    registry.register(old)
    with pytest.raises(ValueError, match="invalid_identity_generation"):
        registry.rotate_identity(
            new,
            expected_generation=2**64,
            old_key_signature=b"x" * 64,
            new_key_signature=b"x" * 64,
        )
