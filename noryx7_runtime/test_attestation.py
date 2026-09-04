import dataclasses
import hashlib

import pytest

from .attestation import (
    AttestationChainVerifier,
    Ed25519AttestationSigner,
    Ed25519AttestationVerifier,
    IdentityBoundAttestationVerifier,
    attestation_digest,
    signed_attestation,
    verify_attestation,
)
from .contracts import Attestation
from core.identity import AgentIdentityAuthority, IdentityRegistry


def make_attestation(signer=None, **changes):
    signer = signer or Ed25519AttestationSigner.generate()
    fingerprint = hashlib.sha256(signer.public_key_bytes).hexdigest()
    value = Attestation(
        execution_id="exec-1",
        principal_id="principal-1",
        step_id="step-1",
        agent_id="agent-1",
        agent_key_fingerprint=fingerprint,
        action_digest="a" * 64,
        output_digest="b" * 64,
        verified=True,
        detail="verified",
    )
    return dataclasses.replace(value, **changes)


def make_chain(signer, count=2):
    chain = []
    previous = "0" * 64
    for index in range(count):
        attestation = make_attestation(
            signer,
            step_id=f"step-{index + 1}",
            action_digest=hashlib.sha256(f"action-{index}".encode()).hexdigest(),
            output_digest=hashlib.sha256(f"output-{index}".encode()).hexdigest(),
            previous_attestation_digest=previous,
        )
        attestation = signed_attestation(attestation, signer)
        chain.append(attestation)
        previous = attestation_digest(attestation)
    return chain


def test_signature_binds_complete_execution_identity_and_result_chain():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(signer), signer)
    assert verify_attestation(signed, signer)
    for field, value in (
        ("execution_id", "exec-2"),
        ("principal_id", "principal-2"),
        ("step_id", "step-2"),
        ("agent_id", "agent-2"),
        ("agent_key_fingerprint", "c" * 64),
        ("action_digest", "c" * 64),
        ("output_digest", "d" * 64),
        ("verified", False),
        ("detail", "forged"),
    ):
        assert not verify_attestation(dataclasses.replace(signed, **{field: value}), signer)


def test_signature_cannot_be_replayed_with_another_key():
    signer = Ed25519AttestationSigner.generate()
    other = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(signer), signer)
    assert verify_attestation(signed, signer)
    assert not verify_attestation(signed, other)


def test_signature_cannot_be_transplanted_to_another_execution():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(signer), signer)
    transplanted = dataclasses.replace(signed, execution_id="exec-attacker")
    assert not verify_attestation(transplanted, signer)


def test_independent_public_key_verifier_accepts_valid_signature():
    signer = Ed25519AttestationSigner.generate()
    verifier = Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes)
    signed = signed_attestation(make_attestation(signer), signer)
    assert verifier.verify(signed, signed.signature)


def test_identity_registry_rejects_public_key_replacement_and_identity_swap():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    signer = Ed25519AttestationSigner(private_key)
    verifier = IdentityBoundAttestationVerifier(registry)
    signed = signed_attestation(make_attestation(signer), signer)
    assert verifier.verify(signed, signed.signature)
    replacement, replacement_key = AgentIdentityAuthority.generate("agent-1")
    replacement_signer = Ed25519AttestationSigner(replacement_key)
    forged = signed_attestation(make_attestation(replacement_signer, agent_id="agent-1"), replacement_signer)
    assert not verifier.verify(forged, forged.signature)
    swapped = dataclasses.replace(signed, agent_id="other-agent")
    assert not verifier.verify(swapped, signed.signature)


def test_revoked_identity_is_rejected_even_with_valid_signature():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    signer = Ed25519AttestationSigner(private_key)
    verifier = IdentityBoundAttestationVerifier(registry)
    signed = signed_attestation(make_attestation(signer), signer)
    registry.revoke("agent-1")
    assert not verifier.verify(signed, signed.signature)


def test_malformed_digest_and_signature_fail_closed():
    signer = Ed25519AttestationSigner.generate()
    malformed = make_attestation(signer, action_digest="not-a-digest")
    with pytest.raises(ValueError):
        verify_attestation(malformed, signer)
    assert not verify_attestation(make_attestation(signer, signature=b"x"), signer)


def test_domain_separation_prevents_cross_protocol_message_reuse():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(signer), signer)
    assert verify_attestation(signed, signer)
    assert signed.signature != signer.private_key.sign(b"other-protocol" + signed.execution_id.encode())


def test_chain_verifier_accepts_ordered_execution_bound_chain():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    assert verifier.verify_chain(make_chain(signer, 3))


def test_chain_rejects_cross_execution_replay():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    chain = make_chain(signer, 2)
    forged = dataclasses.replace(chain[1], execution_id="exec-attacker")
    assert not verifier.verify_chain([chain[0], forged])


def test_chain_rejects_previous_digest_swap_and_skipped_link():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    chain = make_chain(signer, 3)
    swapped = dataclasses.replace(chain[2], previous_attestation_digest="f" * 64)
    assert not verifier.verify_chain([chain[0], chain[1], swapped])
    assert not verifier.verify_chain([chain[0], chain[2]])


def test_chain_rejects_reordered_attestations():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    chain = make_chain(signer, 3)
    assert not verifier.verify_chain([chain[0], chain[2], chain[1]])


def test_chain_rejects_attestation_tampering_even_when_chain_pointer_is_preserved():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    chain = make_chain(signer, 2)
    tampered = dataclasses.replace(chain[1], output_digest="c" * 64)
    assert not verifier.verify_chain([chain[0], tampered])


def test_chain_rejects_runtime_and_principal_swaps():
    signer = Ed25519AttestationSigner.generate()
    verifier = AttestationChainVerifier(Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes))
    chain = make_chain(signer, 2)
    assert not verifier.verify_chain([chain[0], dataclasses.replace(chain[1], runtime_id="other-runtime")])
    assert not verifier.verify_chain([chain[0], dataclasses.replace(chain[1], principal_id="other-principal")])


def test_provenance_binding_is_signature_bound():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(
        make_attestation(
            signer,
            provenance_digest="e" * 64,
            provenance_seal=b"s" * 32,
        ),
        signer,
    )
    assert verify_attestation(signed, signer)
    assert not verify_attestation(dataclasses.replace(signed, provenance_digest="f" * 64), signer)
    assert not verify_attestation(dataclasses.replace(signed, provenance_seal=b"t" * 32), signer)
