import pytest

from core.interaction_context import InteractionContext
from core.recovery import RecoveryState
from core.runtime import NORYXRuntime
from core.user_understanding import SignalKind, UserSignal
from core.orchestration import OrchestrationStage


def _context():
    signal = UserSignal(SignalKind.FORMAT, "detailed", 0.8, ("runtime-test",))
    return InteractionContext("profile-runtime", (signal,), "ctx-runtime")


def test_runtime_and_hypersynth_share_the_same_recovery_controller():
    runtime = NORYXRuntime()
    assert runtime.hypersynth.recovery is runtime.recovery
    assert runtime.security.recovery is runtime.recovery
    assert runtime.hypersynth.security.recovery is runtime.recovery


def test_runtime_rejection_helper_is_terminal_and_fail_closed():
    runtime = NORYXRuntime()
    task = pytest.importorskip("core.contracts").TaskSpec(
        "runtime-reject-test", "compute", "test objective", "test input"
    )
    envelope = runtime._context_envelope(task, _context(), "exec-runtime")
    rejected = runtime._rejection(envelope, task.task_id, "test_failure", runtime.audit)
    assert rejected["status"] == "rejected"
    assert rejected["orchestration_stage"] == OrchestrationStage.REJECTED.value


def test_recovery_state_blocks_hypersynth_execution_before_cognition():
    runtime = NORYXRuntime()
    runtime.recovery.incident()
    assert runtime.recovery.state is RecoveryState.INCIDENT
    task = pytest.importorskip("core.contracts").TaskSpec(
        "runtime-recovery-test", "compute", "test objective", "test input"
    )
    result = runtime.run_hypersynth(task, _context())
    assert result["status"] == "rejected"
    assert result["reason"] == "recovery_state_denies_execution"
