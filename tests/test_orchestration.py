import pytest

from core.interaction_context import InteractionContext
from core.orchestration import OrchestrationCoordinator, OrchestrationEnvelope, OrchestrationStage


def _envelope():
    context = InteractionContext(
        context_id="ctx-test",
        locale="it-IT",
        timezone="Europe/Rome",
        channel="test",
    )
    return OrchestrationEnvelope(
        request_id="req-test",
        principal_id="exec-test",
        operation="compute",
        interaction_context=context,
    )


def test_reject_from_every_non_terminal_stage():
    envelope = _envelope()
    for target in (
        OrchestrationStage.UNDERSTOOD,
        OrchestrationStage.REPRESENTED,
        OrchestrationStage.ROUTED,
        OrchestrationStage.PLANNED,
        OrchestrationStage.EXECUTING,
        OrchestrationStage.VERIFYING,
    ):
        envelope, _ = OrchestrationCoordinator.transition(envelope, target)
        rejected, transition = OrchestrationCoordinator.reject(envelope)
        assert rejected.stage is OrchestrationStage.REJECTED
        assert transition.previous is target
        assert transition.current is OrchestrationStage.REJECTED
        envelope = _envelope()


def test_rejected_and_committed_are_terminal():
    envelope = _envelope()
    rejected, _ = OrchestrationCoordinator.reject(envelope)
    with pytest.raises(ValueError, match="terminal_orchestration_stage"):
        OrchestrationCoordinator.reject(rejected)

    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.UNDERSTOOD)
    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.REPRESENTED)
    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.ROUTED)
    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.PLANNED)
    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.EXECUTING)
    envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.VERIFYING)
    committed, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.COMMITTED)
    with pytest.raises(ValueError, match="terminal_orchestration_stage"):
        OrchestrationCoordinator.reject(committed)
