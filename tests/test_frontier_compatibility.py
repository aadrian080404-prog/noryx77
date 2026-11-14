import pytest

from core.contracts import TaskSpec
from core.hypersynth_runtime import HypersynthRuntime
from core.runtime import NORYXRuntime


def test_top_level_runtime_uses_bounded_default_context():
    runtime = NORYXRuntime()
    result = runtime.run(TaskSpec("frontier-runtime", "compute", "objective", "input"))
    assert result["status"] == "completed"
    assert result["orchestration_stage"] == "committed"


def test_hypersynth_contract_validation_precedes_optional_identity_binding():
    runtime = HypersynthRuntime()
    runtime.kernel.run = lambda task, deadline_check=None: {"status": "completed", "results": ()}
    result = runtime.run(TaskSpec("frontier-hypersynth", "search", "objective", "input"))
    assert result["status"] == "rejected"
    assert result["phase"] == "verification"
    assert result["verification"].reason == "invalid_kernel_verification"


def test_hypersynth_non_mapping_kernel_result_is_fail_closed():
    runtime = HypersynthRuntime()
    runtime.kernel.run = lambda task, deadline_check=None: object()
    result = runtime.run(TaskSpec("frontier-kernel-contract", "search", "objective", "input"))
    assert result["status"] == "rejected"
    assert result["phase"] == "execution"
    assert result["verification"].reason == "malformed_kernel_result"


def test_self_dispatch_is_rejected_before_cross_front_policy():
    from ecosystem.boundaries import Front, make_intent
    from ecosystem.dispatch_contract import make_receipt

    intent = make_intent(Front.JARVIS, "execute", b"x", principal_id="frontier-principal")
    with pytest.raises(ValueError, match="self_dispatch_denied"):
        make_receipt(intent, source=Front.JARVIS, target=Front.JARVIS,
                     execution_id="frontier-exec", accepted=False,
                     reason="denied", evidence=b"x")
