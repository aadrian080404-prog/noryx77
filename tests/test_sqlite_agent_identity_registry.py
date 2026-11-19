import threading

import pytest

from core.identity import AgentIdentityAuthority, identity_rotation_message
from core.sqlite_agent_identity_registry import SQLiteAgentIdentityRegistry


def _signed_rotation(agent_id="durable-agent"):
    old, old_private = AgentIdentityAuthority.generate(agent_id)
    new, new_private = AgentIdentityAuthority.generate(agent_id)
    message = identity_rotation_message(
        agent_id, old.public_key, new.public_key, 1
    )
    return old, new, old_private, old_private.sign(message), new_private.sign(message)


def test_durable_registry_persists_identity_generation_and_rotation(tmp_path):
    old, new, _old_private, old_proof, new_proof = _signed_rotation()
    db = tmp_path / "identity-registry.db"
    registry = SQLiteAgentIdentityRegistry(db)
    try:
        assert registry.register(old) == 1
        assert registry.rotate_identity(
            new,
            expected_generation=1,
            old_key_signature=old_proof,
            new_key_signature=new_proof,
        ) == 2
        assert registry.is_trusted(new)
        assert not registry.is_trusted(old)
    finally:
        registry.close()

    reopened = SQLiteAgentIdentityRegistry(db)
    try:
        assert reopened.generation(new.agent_id) == 2
        assert reopened.is_trusted(new)
        assert not reopened.is_trusted(old)
    finally:
        reopened.close()


def test_durable_registry_rejects_invalid_proof_without_mutating_state(tmp_path):
    old, new, _old_private, _old_proof, new_proof = _signed_rotation()
    registry = SQLiteAgentIdentityRegistry(tmp_path / "identity-invalid-proof.db")
    try:
        registry.register(old)
        with pytest.raises(PermissionError, match="identity_rotation_proof_invalid"):
            registry.rotate_identity(
                new, expected_generation=1,
                old_key_signature=b"x" * 64, new_key_signature=new_proof,
            )
        assert registry.generation(old.agent_id) == 1
        assert registry.is_trusted(old)
    finally:
        registry.close()


def test_durable_registry_revocation_survives_restart_and_is_terminal(tmp_path):
    old, new, _old_private, _old_proof, _new_proof = _signed_rotation()
    db = tmp_path / "identity-revoked.db"
    registry = SQLiteAgentIdentityRegistry(db)
    registry.register(old)
    registry.revoke(old.agent_id)
    registry.close()

    reopened = SQLiteAgentIdentityRegistry(db)
    try:
        assert not reopened.is_trusted(old)
        with pytest.raises(PermissionError, match="agent_identity_not_active"):
            reopened.generation(old.agent_id)
        with pytest.raises(ValueError, match="agent_identity_already_registered"):
            reopened.register(new)
    finally:
        reopened.close()


def test_two_registry_instances_allow_only_one_competing_rotation(tmp_path):
    old, new_a, old_private, old_proof_a, new_proof_a = _signed_rotation("race-agent")
    new_b, new_b_private = AgentIdentityAuthority.generate("race-agent")
    message_b = identity_rotation_message(
        "race-agent", old.public_key, new_b.public_key, 1
    )
    old_proof_b = old_private.sign(message_b)
    new_proof_b = new_b_private.sign(message_b)
    db = tmp_path / "identity-race.db"
    first = SQLiteAgentIdentityRegistry(db)
    second = SQLiteAgentIdentityRegistry(db)
    try:
        first.register(old)
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()

        def rotate(registry, candidate, old_proof, new_proof):
            barrier.wait()
            try:
                result = registry.rotate_identity(
                    candidate, expected_generation=1,
                    old_key_signature=old_proof, new_key_signature=new_proof,
                )
                value = ("ok", result)
            except PermissionError as exc:
                value = ("denied", str(exc))
            with outcome_lock:
                outcomes.append(value)

        threads = [
            threading.Thread(target=rotate, args=(first, new_a, old_proof_a, new_proof_a)),
            threading.Thread(target=rotate, args=(second, new_b, old_proof_b, new_proof_b)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert all(not thread.is_alive() for thread in threads)
        assert sum(value[0] == "ok" for value in outcomes) == 1
        assert sum(value[0] == "denied" for value in outcomes) == 1
        assert first.generation("race-agent") == 2
    finally:
        first.close()
        second.close()


def test_persistent_registry_implements_identity_authority_trust_contract(tmp_path):
    identity, private_key = AgentIdentityAuthority.generate("protocol-agent")
    registry = SQLiteAgentIdentityRegistry(tmp_path / "identity-protocol.db")
    try:
        attestation = AgentIdentityAuthority.sign(
            identity, private_key, b"boot-state:v1"
        )
        assert not AgentIdentityAuthority.verify(attestation, registry)
        registry.register(identity)
        assert AgentIdentityAuthority.verify(attestation, registry)
        assert AgentIdentityAuthority.verify_identity(identity, registry)
        result = registry.with_trusted_identity(
            identity.agent_id, lambda trusted: trusted.public_key
        )
        assert result == identity.public_key
    finally:
        registry.close()
