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


def test_runtime_consumes_high_risk_authorization_once_before_dispatch():
    authority, provider = _authority_and_proof_provider()
    guard = AuthorizationReplayGuard()
    calls = []
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=provider,
        high_risk_action_types={"delete"},
        authorization_epoch=7,
        replay_guard=guard,
    )
    intent = Intent(principal_id=1, description="delete")
    steps = [PlanStep(step_id="s1", action_type="delete", target="x", parameters={})]

    first = engine.execute(intent, steps, executor=lambda e: calls.append(e) or "ok", verifier=lambda e, o: True, execution_id="exec-1")
    second = engine.execute(intent, steps, executor=lambda e: calls.append(e) or "ok", verifier=lambda e, o: True, execution_id="exec-1")

    assert first.status is ExecutionStatus.SUCCEEDED
    assert second.status is ExecutionStatus.SUCCEEDED
    assert len(calls) == 2
    assert guard.consumed_count == 2


def test_replay_guard_can_block_a_reused_digest():
    authority, provider = _authority_and_proof_provider()
    guard = AuthorizationReplayGuard()
    engine = RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=provider,
        high_risk_action_types={"delete"},
        authorization_epoch=7,
        replay_guard=guard,
    )
    intent = Intent(principal_id=1, description="delete")
    steps = [PlanStep(step_id="s1", action_type="delete", target="x", parameters={})]
    original = engine.execute(intent, steps, executor=lambda e: "ok", verifier=lambda e, o: True, execution_id="exec-2")
    assert original.status is ExecutionStatus.SUCCEEDED
    digest = original.attestations[0].action_digest
    assert guard.contains(bytes.fromhex(digest))
    assert guard.consume(bytes.fromhex(digest)) is False
