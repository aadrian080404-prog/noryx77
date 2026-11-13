import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authorization_replay import AuthorizationReplayGuard
from core.multiauth import SignedApprovalAuthority, SignedAuthorizationProof, sign_approval

from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def _authority_and_proof_provider():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    authority = SignedApprovalAuthority(required_threshold=1, trusted_keys={"owner": public})

    def provider(envelope, digest):
        approval = sign_approval(
            "owner", private,
            action_id=envelope.execution_id,
            epoch=7,
            action_statement=digest,
        )
        return SignedAuthorizationProof(
            envelope.execution_id, 7, digest, (approval,), 1
        )

    return authority, provider


def _authorization_replay_token(envelope):
    statement = {
        "execution_id": envelope.execution_id,
        "principal_id": envelope.principal_id,
        "step_id": envelope.step_id,
        "action_type": envelope.action_type,
        "target": envelope.target,
        "parameters": dict(envelope.parameters),
    }
    encoded = json.dumps(
        statement,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return bytes.fromhex(hashlib.sha256(encoded).hexdigest())


def test_runtime_rejects_reuse_of_the_same_high_risk_authorization(tmp_path):
    authority, provider = _authority_and_proof_provider()
    guard = AuthorizationReplayGuard(path=str(tmp_path / "runtime-replay-1.sqlite3"))
    calls = []
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=provider,
        high_risk_action_types={"delete"},
        authorization_epoch=7,
        replay_guard=guard,
    )
    intent = Intent(text="delete", principal_id="principal-1")
    steps = [PlanStep(step_id="s1", action_type="delete", target="x", parameters={})]

    first = engine.execute(intent, steps, executor=lambda e: calls.append(e) or "ok", verifier=lambda e, o: True, execution_id="exec-1")
    second = engine.execute(intent, steps, executor=lambda e: calls.append(e) or "ok", verifier=lambda e, o: True, execution_id="exec-1")

    assert first.status is ExecutionStatus.SUCCEEDED
    assert second.status is ExecutionStatus.FAILED
    assert second.error == "PermissionError"
    assert len(calls) == 1
    assert guard.consumed_count == 1


def test_replay_guard_tracks_the_signed_action_statement_not_attempt_nonce(tmp_path):
    authority, provider = _authority_and_proof_provider()
    guard = AuthorizationReplayGuard(path=str(tmp_path / "runtime-replay-2.sqlite3"))
    calls = []
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=provider,
        high_risk_action_types={"delete"},
        authorization_epoch=7,
        replay_guard=guard,
    )
    intent = Intent(text="delete", principal_id="principal-1")
    steps = [PlanStep(step_id="s1", action_type="delete", target="x", parameters={})]
    original = engine.execute(
        intent,
        steps,
        executor=lambda envelope: calls.append(envelope) or "ok",
        verifier=lambda e, o: True,
        execution_id="exec-2",
    )

    assert original.status is ExecutionStatus.SUCCEEDED
    token = _authorization_replay_token(calls[0])
    assert guard.contains(token)
    assert guard.consume(token) is False
    assert token != bytes.fromhex(original.attestations[0].action_digest)
