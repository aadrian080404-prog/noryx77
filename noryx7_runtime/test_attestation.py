import dataclasses

from .attestation import Ed25519AttestationSigner, signed_attestation, verify_attestation
from .contracts import Attestation


def make_attestation(**changes):
    value = Attestation(
        execution_id="exec-1",
        principal_id="principal-1",
        step_id="step-1",
        agent_id="agent-1",
        action_digest="a" * 64,
        output_digest="b" * 64,
        verified=True,
        detail="verified",
    )
    return dataclasses.replace(value, **changes)


def test_signature_binds_complete_execution_identity_and_result_chain():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(), signer)
    assert verify_attestation(signed, signer)
    for field, value in (
        ("execution_id", "exec-2"),
        ("principal_id", "principal-2"),
        ("step_id", "step-2"),
        ("agent_id", "agent-2"),
        ("action_digest", "c" * 64),
        ("output_digest", "d" * 64),
        ("verified", False),
        ("detail", "forged"),
    ):
        assert not verify_attestation(dataclasses.replace(signed, **{field: value}), signer)


def test_signature_cannot_be_replayed_with_another_key():
    signer = Ed25519AttestationSigner.generate()
    other = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(), signer)
    assert verify_attestation(signed, signer)
    assert not verify_attestation(signed, other)


def test_signature_cannot_be_transplanted_to_another_execution():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(), signer)
    transplanted = dataclasses.replace(signed, execution_id="exec-attacker")
    assert not verify_attestation(transplanted, signer)


def test_malformed_digest_and_signature_fail_closed():
    signer = Ed25519AttestationSigner.generate()
    malformed = make_attestation(action_digest="not-a-digest")
    try:
        verify_attestation(malformed, signer)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed digest must fail closed")
    assert not verify_attestation(make_attestation(signature=b"x"), signer)


def test_domain_separation_prevents_cross_protocol_message_reuse():
    signer = Ed25519AttestationSigner.generate()
    signed = signed_attestation(make_attestation(), signer)
    assert verify_attestation(signed, signer)
    assert signed.signature != signer.private_key.sign(b"other-protocol" + signed.execution_id.encode())
