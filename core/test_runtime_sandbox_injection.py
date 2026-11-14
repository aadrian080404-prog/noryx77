from core.actions import AuthorizationAuthority
from core.authorization_replay import AuthenticatedAuthorizationReplayGuard
from core.contracts import ActionSpec
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.runtime import NORYXRuntime


class StubSandboxAdapter:
    environment = "sandboxed_process"

    def __init__(self):
        self.actions = []

    def execute(self, action):
        self.actions.append(action)
        return {"status": "executed"}


def test_canonical_runtime_exposes_explicit_sandbox_adapter():
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(sandboxed_process_adapter=adapter)

    assert runtime.hypersynth.sandboxed_process_adapter is adapter
    assert runtime.capability_registry.resolve("sandboxed_process") is not None
    assert runtime.capability_registry.risk("sandboxed_process") == "high"


def test_canonical_runtime_keeps_process_capability_disabled_by_default():
    runtime = NORYXRuntime()
    assert runtime.capability_registry.resolve("sandboxed_process") is None


def test_canonical_runtime_binds_collaboration_to_identity_registry():
    runtime = NORYXRuntime()
    assert runtime.hypersynth.collaboration.identity_registry is runtime.identity_registry



def test_canonical_runtime_accepts_only_durable_authenticated_registry_bound_authority(tmp_path):
    registry = IdentityRegistry()
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-test-key",
        path=str(tmp_path / "authorization-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )

    runtime = NORYXRuntime(identity_registry=registry, authorization_authority=authority)

    assert runtime.identity_registry is registry
    assert runtime.action_gate.authorization is authority
    assert runtime.hypersynth.action_gate.authorization is authority
    replay_guard.close()


def test_canonical_runtime_rejects_ephemeral_authority(tmp_path):
    import pytest

    registry = IdentityRegistry()
    authority = AuthorizationAuthority(b"a" * 32, identity_registry=registry)
    with pytest.raises(ValueError, match="invalid_runtime_authorization_authority"):
        NORYXRuntime(identity_registry=registry, authorization_authority=authority)


def test_canonical_runtime_rejects_authority_bound_to_another_registry(tmp_path):
    import pytest

    registry = IdentityRegistry()
    other_registry = IdentityRegistry()
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-test-key",
        path=str(tmp_path / "other-authorization-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=other_registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    with pytest.raises(ValueError, match="invalid_runtime_authorization_authority"):
        NORYXRuntime(identity_registry=registry, authorization_authority=authority)
    replay_guard.close()



def test_canonical_runtime_keeps_high_risk_process_action_fail_closed_without_authority():
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(sandboxed_process_adapter=adapter)
    action = ActionSpec(
        action_id="sandbox-action",
        action_type="sandboxed_process",
        target="workspace",
        parameters={"action_id": "sandbox-action", "argv": ["/usr/bin/true"]},
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-no-authority",
    )
    output, decision = runtime.tool_executor.execute(
        action,
        execution_id="exec-no-authority",
    )
    assert output is None
    assert not decision.valid
    assert decision.reason == "authorization_required"
    assert adapter.actions == []

def test_canonical_runtime_dispatches_authorized_sandbox_action_once(tmp_path):
    registry = IdentityRegistry()
    principal, _private_key = AgentIdentityAuthority.generate("sandbox-operator")
    registry.register(principal)
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-dispatch-test-key",
        path=str(tmp_path / "dispatch-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(
        identity_registry=registry,
        authorization_authority=authority,
        sandboxed_process_adapter=adapter,
    )
    action = ActionSpec(
        action_id="sandbox-authorized-once",
        action_type="sandboxed_process",
        target="workspace",
        parameters={"action_id": "sandbox-authorized-once", "argv": ["/usr/bin/true"]},
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-sandbox-authorized-once",
    )
    grant = authority.issue(
        action,
        "exec-sandbox-authorized-once",
        principal=principal,
    )
    try:
        output, check = runtime.tool_executor.execute(
            action,
            execution_id="exec-sandbox-authorized-once",
            grant=grant,
            principal=principal,
        )
        assert check.valid
        assert output == {"status": "executed"}
        assert len(adapter.actions) == 1

        replay_output, replay_check = runtime.tool_executor.execute(
            action,
            execution_id="exec-sandbox-authorized-once",
            grant=grant,
            principal=principal,
        )
        assert replay_output is None
        assert not replay_check.valid
        assert replay_check.reason == "invalid_authorization_grant"
        assert len(adapter.actions) == 1
    finally:
        replay_guard.close()


def test_canonical_runtime_rejects_concurrent_replay_before_second_dispatch(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    registry = IdentityRegistry()
    principal, _private_key = AgentIdentityAuthority.generate("sandbox-concurrent-operator")
    registry.register(principal)
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-concurrent-replay-test-key",
        path=str(tmp_path / "concurrent-dispatch-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(
        identity_registry=registry,
        authorization_authority=authority,
        sandboxed_process_adapter=adapter,
    )
    action = ActionSpec(
        action_id="sandbox-concurrent-once",
        action_type="sandboxed_process",
        target="workspace",
        parameters={"action_id": "sandbox-concurrent-once", "argv": ["/usr/bin/true"]},
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-sandbox-concurrent-once",
    )
    grant = authority.issue(action, "exec-sandbox-concurrent-once", principal=principal)
    barrier = Barrier(3)

    def dispatch():
        barrier.wait(timeout=10)
        return runtime.tool_executor.execute(
            action,
            execution_id="exec-sandbox-concurrent-once",
            grant=grant,
            principal=principal,
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(dispatch) for _ in range(2)]
            barrier.wait(timeout=10)
            results = [future.result(timeout=15) for future in futures]
        assert sum(1 for output, decision in results if decision.valid and output == {"status": "executed"}) == 1
        assert sum(1 for output, decision in results if not decision.valid) == 1
        assert len(adapter.actions) == 1
    finally:
        replay_guard.close()


def test_authorized_runtime_dispatches_through_real_bubblewrap_once(tmp_path, monkeypatch):
    import os
    import sys
    import pytest

    if os.environ.get("NORYX7_RUN_BWRAP_E2E") != "1" or sys.platform != "linux":
        pytest.skip("requires the real Bubblewrap integration runner")

    from core.os_sandbox import BubblewrapSandboxRunner, SandboxLimits
    from core.sandboxed_execution import SandboxedProcessAdapter

    workspace = tmp_path / "runtime-workspace"
    workspace.mkdir()
    runner = BubblewrapSandboxRunner()
    adapter = SandboxedProcessAdapter(
        runner,
        workspace=workspace,
        limits=SandboxLimits(
            cpu_seconds=3,
            memory_bytes=64 * 1024 * 1024,
            file_size_bytes=4096,
            open_files=20,
            processes=5,
            wall_seconds=10,
            output_bytes=4096,
        ),
    )

    registry = IdentityRegistry()
    principal, _private_key = AgentIdentityAuthority.generate("bubblewrap-runtime-operator")
    registry.register(principal)
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="bubblewrap-runtime-e2e-key",
        path=str(tmp_path / "bubblewrap-runtime-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    from core.sqlite_audit import SQLiteAuditLog
    from core.journal_integrity import InMemoryMonotonicAnchor

    audit_path = tmp_path / "bubblewrap-runtime-audit.sqlite3"
    audit_log = SQLiteAuditLog(str(audit_path))
    runtime = NORYXRuntime(
        audit_log=audit_log,
        identity_registry=registry,
        authorization_authority=authority,
        sandboxed_process_adapter=adapter,
    )
    action = ActionSpec(
        action_id="bubblewrap-runtime-e2e",
        action_type="sandboxed_process",
        target="workspace",
        parameters={
            "action_id": "bubblewrap-runtime-e2e",
            "argv": [
                "/usr/bin/python3",
                "-I",
                "-c",
                "from pathlib import Path; Path('/workspace/authorized-marker').write_text('authorized'); print('sandbox-dispatch-ok')",
            ],
        },
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-bubblewrap-runtime-e2e",
    )
    grant = authority.issue(
        action,
        "exec-bubblewrap-runtime-e2e",
        principal=principal,
    )
    try:
        output, decision = runtime.tool_executor.execute(
            action,
            execution_id="exec-bubblewrap-runtime-e2e",
            grant=grant,
            principal=principal,
        )
        assert decision.valid
        assert output.exit_code == 0
        assert output.stdout.strip() == b"sandbox-dispatch-ok"
        assert (workspace / "authorized-marker").read_text() == "authorized"

        replay_output, replay_decision = runtime.tool_executor.execute(
            action,
            execution_id="exec-bubblewrap-runtime-e2e",
            grant=grant,
            principal=principal,
        )
        assert replay_output is None
        assert not replay_decision.valid
        assert replay_decision.reason == "invalid_authorization_grant"
        assert (workspace / "authorized-marker").read_text() == "authorized"

        audit_events = audit_log.snapshot()
        assert [event["event"] for event in audit_events] == [
            "sandbox_process_dispatch_started",
            "sandbox_process_dispatch_completed",
        ]
        completed = audit_events[-1]
        assert completed["exit_code"] == 0
        assert completed["stdout_sha256"]
        assert completed["stderr_sha256"]
        assert "sandbox-dispatch-ok" not in str(audit_events)

        anchor = InMemoryMonotonicAnchor()
        anchored_head = audit_log.verify_and_advance_anchor(anchor)
        assert anchored_head.sequence == 2
        audit_log.close()

        reopened_audit = SQLiteAuditLog(str(audit_path))
        try:
            assert reopened_audit.verify_integrity()
            assert reopened_audit.snapshot() == audit_events
            assert reopened_audit.verify_and_advance_anchor(anchor) == anchored_head
        finally:
            reopened_audit.close()
    finally:
        if not audit_log._closed:
            audit_log.close()
        replay_guard.close()


def test_sandbox_dispatch_surfaces_uncertain_outcome_if_completion_audit_fails():
    import pytest
    from core.audit import AuditLog

    class CompletionFailingAudit(AuditLog):
        def record(self, event, **data):
            if event == "sandbox_process_dispatch_completed":
                raise OSError("simulated_durable_audit_failure")
            return super().record(event, **data)

    adapter = StubSandboxAdapter()
    audit = CompletionFailingAudit()
    runtime = NORYXRuntime(
        audit_log=audit,
        sandboxed_process_adapter=adapter,
    )
    dispatch = runtime.capability_registry.resolve("sandboxed_process")

    with pytest.raises(RuntimeError, match="sandbox_process_audit_commit_uncertain"):
        dispatch(
            "workspace",
            {"action_id": "audit-uncertain-action", "argv": ["/usr/bin/true"]},
        )

    assert len(adapter.actions) == 1
    assert [event["event"] for event in audit.snapshot()] == [
        "sandbox_process_dispatch_started",
    ]
