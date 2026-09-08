from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authorization_replay import AuthorizationReplayGuard
from core.multiauth import SignedApprovalAuthority, SignedAuthorizationProof, sign_approval

from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def step(action_type):
    return PlanStep("step-1", action_type, "target", {"amount": 10}, ())


def authority_and_keys():
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    authority = SignedApprovalAuthority(
        required_threshold=2,
        trusted_keys={"A": a.public_key().public_bytes_raw(), "B": b.public_key().public_bytes_raw()},
    )
    return authority, a, b


def proof_provider(a, b, epoch=7, mutate=False, override_epoch=None):
    def provider(envelope, digest):
        statement = digest[:-1] + bytes([digest[-1] ^ 1]) if mutate else digest
        signed_epoch = epoch if override_epoch is None else override_epoch
        return SignedAuthorizationProof(
            action_id=envelope.execution_id,
            epoch=signed_epoch,
            action_statement=statement,
            approvals=(
                sign_approval("A", a, action_id=envelope.execution_id, epoch=signed_epoch, action_statement=statement),
                sign_approval("B", b, action_id=envelope.execution_id, epoch=signed_epoch, action_statement=statement),
            ),
            threshold=2,
        )
    return provider


def configured_engine(authority, provider, replay_guard=None):
    return RuntimeEngine(
        multi_auth_authority=authority,
        authorization_provider=provider,
        high_risk_action_types={"money.transfer"},
        authorization_epoch=7,
        replay_guard=replay_guard or AuthorizationReplayGuard(),
    )


def test_high_risk_requires_explicit_replay_guard():
    authority, a, b = authority_and_keys()
    try:
        RuntimeEngine(
            multi_auth_authority=authority,
            authorization_provider=proof_provider(a, b),
            high_risk_action_types={"money.transfer"},
            authorization_epoch=7,
        )
    except ValueError as exc:
        assert str(exc) == "high_risk_actions_require_replay_guard"
    else:
        raise AssertionError("high-risk runtime accepted without replay guard")


def test_high_risk_valid_multi_auth_is_required_before_executor():
    authority, a, b = authority_and_keys()
    called = []
    engine = configured_engine(authority, proof_provider(a, b), AuthorizationReplayGuard())
    result = engine.execute(
        Intent("run", "user"),
        [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-valid",
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert called == ["step-1"]


def test_high_risk_replay_is_rejected_before_second_side_effect():
    authority, a, b = authority_and_keys()
    replay = AuthorizationReplayGuard()
    provider = proof_provider(a, b)
    engine = configured_engine(authority, provider, replay)
    called = []
    first = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-replay",
    )
    second = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-replay",
    )
    assert first.status is ExecutionStatus.SUCCEEDED
    assert second.status is ExecutionStatus.FAILED
    assert second.error == "PermissionError"
    assert called == ["step-1"]


def test_high_risk_missing_proof_fails_before_side_effect():
    authority, _, _ = authority_and_keys()
    called = []
    engine = configured_engine(authority, lambda envelope, digest: None)
    result = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-missing",
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert called == []


def test_high_risk_wrong_signed_statement_fails_before_side_effect():
    authority, a, b = authority_and_keys()
    called = []
    engine = configured_engine(authority, proof_provider(a, b, mutate=True))
    result = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-mutate",
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert called == []


def test_high_risk_wrong_epoch_fails_before_side_effect():
    authority, a, b = authority_and_keys()
    called = []
    engine = configured_engine(authority, proof_provider(a, b, override_epoch=6))
    result = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-epoch",
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert called == []


def test_revoked_approver_fails_before_side_effect():
    authority, a, b = authority_and_keys()
    authority.revoke("A")
    called = []
    engine = configured_engine(authority, proof_provider(a, b))
    result = engine.execute(
        Intent("run", "user"), [step("money.transfer")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
        execution_id="exec-revoked",
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert called == []


def test_non_high_risk_action_remains_compatible_without_multi_auth():
    called = []
    result = RuntimeEngine().execute(
        Intent("run", "user"), [step("calendar.read")],
        executor=lambda action: called.append(action.step_id) or "ok",
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert called == ["step-1"]
