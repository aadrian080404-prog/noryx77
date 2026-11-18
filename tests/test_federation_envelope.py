import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.federation_envelope import (
    EnvelopeRejected,
    ExecutionEnvelopeVerifier,
    SQLiteEnvelopeReplayStore,
    SignedExecutionEnvelope,
    sign_execution_envelope,
)


def _unsigned(nonce=b"n" * 32, issued_at=100, expires_at=160):
    return SignedExecutionEnvelope(
        schema_version=1,
        execution_id="exec-001",
        principal_id="principal-001",
        agent_id="agent-001",
        task_type="analysis",
        capabilities=("memory.read", "task.execute"),
        policy_version="policy-v4",
        state_version="state-v9",
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
        issuer_key_id="issuer-v1",
    )


def _verifier(tmp_path, private_key, *, now=lambda: 110, revoked=lambda _key: False):
    store = SQLiteEnvelopeReplayStore(str(tmp_path / "replay.sqlite3"))
    verifier = ExecutionEnvelopeVerifier(
        {"issuer-v1": private_key.public_key()},
        store,
        is_issuer_revoked=revoked,
        is_principal_revoked=lambda _principal: False,
        is_agent_revoked=lambda _agent: False,
        clock=now,
    )
    return verifier, store


def test_signed_envelope_is_verified_and_nonce_consumed(tmp_path):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(), issuer_key_id="issuer-v1", signing_key=key
    )
    verifier, store = _verifier(tmp_path, key)
    try:
        assert verifier.verify_and_consume(envelope) == envelope
        with pytest.raises(EnvelopeRejected, match="execution_envelope_replayed"):
            verifier.verify_and_consume(envelope)
    finally:
        store.close()


def test_modified_capability_is_rejected_even_if_other_fields_are_valid(tmp_path):
    from dataclasses import replace

    key = Ed25519PrivateKey.generate()
    signed = sign_execution_envelope(
        _unsigned(), issuer_key_id="issuer-v1", signing_key=key
    )
    tampered = replace(signed, capabilities=("memory.read", "admin.root"))
    verifier, store = _verifier(tmp_path, key)
    try:
        with pytest.raises(EnvelopeRejected, match="signature_invalid"):
            verifier.verify_and_consume(tampered)
    finally:
        store.close()


def test_unknown_or_revoked_issuer_is_rejected(tmp_path):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(), issuer_key_id="issuer-v1", signing_key=key
    )
    unknown_store = SQLiteEnvelopeReplayStore(str(tmp_path / "unknown.sqlite3"))
    unknown = ExecutionEnvelopeVerifier(
        {"different-issuer": key.public_key()},
        unknown_store,
        is_issuer_revoked=lambda _key: False,
        is_principal_revoked=lambda _principal: False,
        is_agent_revoked=lambda _agent: False,
        clock=lambda: 110,
    )
    revoked, revoked_store = _verifier(
        tmp_path, key, revoked=lambda _key: True
    )
    try:
        with pytest.raises(EnvelopeRejected, match="unknown_execution_issuer"):
            unknown.verify_and_consume(envelope)
        with pytest.raises(EnvelopeRejected, match="execution_issuer_revoked"):
            revoked.verify_and_consume(envelope)
    finally:
        unknown_store.close()
        revoked_store.close()


@pytest.mark.parametrize(
    ("issued_at", "expires_at", "now", "reason"),
    [
        (100, 109, 110, "expired"),
        (120, 180, 110, "not_yet_valid"),
        (100, 1000, 110, "lifetime_exceeded"),
    ],
)
def test_expired_future_or_overlong_envelope_is_rejected(
    tmp_path, issued_at, expires_at, now, reason
):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(nonce=(str(issued_at) + "x" * 40).encode()[:32],
                  issued_at=issued_at, expires_at=expires_at),
        issuer_key_id="issuer-v1",
        signing_key=key,
    )
    verifier, store = _verifier(tmp_path, key, now=lambda: now)
    try:
        with pytest.raises(EnvelopeRejected, match=reason):
            verifier.verify_and_consume(envelope)
    finally:
        store.close()


def test_replay_guard_survives_verifier_and_database_reopen(tmp_path):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(), issuer_key_id="issuer-v1", signing_key=key
    )
    first = SQLiteEnvelopeReplayStore(str(tmp_path / "durable-replay.sqlite3"))
    verifier = ExecutionEnvelopeVerifier(
        {"issuer-v1": key.public_key()},
        first,
        is_issuer_revoked=lambda _key: False,
        is_principal_revoked=lambda _principal: False,
        is_agent_revoked=lambda _agent: False,
        clock=lambda: 110,
    )
    verifier.verify_and_consume(envelope)
    first.close()

    reopened = SQLiteEnvelopeReplayStore(str(tmp_path / "durable-replay.sqlite3"))
    second_verifier = ExecutionEnvelopeVerifier(
        {"issuer-v1": key.public_key()},
        reopened,
        is_issuer_revoked=lambda _key: False,
        is_principal_revoked=lambda _principal: False,
        is_agent_revoked=lambda _agent: False,
        clock=lambda: 110,
    )
    try:
        with pytest.raises(EnvelopeRejected, match="execution_envelope_replayed"):
            second_verifier.verify_and_consume(envelope)
    finally:
        reopened.close()


def test_revocation_lookup_failure_fails_closed(tmp_path):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(), issuer_key_id="issuer-v1", signing_key=key
    )
    store = SQLiteEnvelopeReplayStore(str(tmp_path / "revocation-failure.sqlite3"))
    verifier = ExecutionEnvelopeVerifier(
        {"issuer-v1": key.public_key()},
        store,
        is_issuer_revoked=lambda _key: (_ for _ in ()).throw(RuntimeError("offline")),
        is_principal_revoked=lambda _principal: False,
        is_agent_revoked=lambda _agent: False,
        clock=lambda: 110,
    )
    try:
        with pytest.raises(EnvelopeRejected, match="revocation_check_unavailable"):
            verifier.verify_and_consume(envelope)
    finally:
        store.close()


def test_invalid_envelope_shapes_are_rejected_before_signing():
    with pytest.raises(ValueError, match="duplicate_capability"):
        SignedExecutionEnvelope(
            1, "exec", "principal", "agent", "task",
            ("task.execute", "task.execute"), "policy", "state",
            100, 120, b"n" * 32, "issuer",
        )
    with pytest.raises(ValueError, match="invalid_nonce"):
        SignedExecutionEnvelope(
            1, "exec", "principal", "agent", "task",
            ("task.execute",), "policy", "state",
            100, 120, b"short", "issuer",
        )



@pytest.mark.parametrize(
    ("principal_revoked", "agent_revoked", "reason"),
    [
        (lambda _principal: True, lambda _agent: False, "execution_principal_revoked"),
        (lambda _principal: False, lambda _agent: True, "execution_agent_revoked"),
    ],
)
def test_revoked_principal_or_agent_is_rejected(tmp_path, principal_revoked, agent_revoked, reason):
    key = Ed25519PrivateKey.generate()
    envelope = sign_execution_envelope(
        _unsigned(nonce=b"z" * 32), issuer_key_id="issuer-v1", signing_key=key
    )
    store = SQLiteEnvelopeReplayStore(str(tmp_path / "identity-revocation.sqlite3"))
    verifier = ExecutionEnvelopeVerifier(
        {"issuer-v1": key.public_key()},
        store,
        is_issuer_revoked=lambda _key: False,
        is_principal_revoked=principal_revoked,
        is_agent_revoked=agent_revoked,
        clock=lambda: 110,
    )
    try:
        with pytest.raises(EnvelopeRejected, match=reason):
            verifier.verify_and_consume(envelope)
    finally:
        store.close()
