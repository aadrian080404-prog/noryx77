from __future__ import annotations

from core.state import StateJournal
from .contracts import Intent, PlanStep, ExecutionStatus
from .engine import RuntimeEngine


def _execute(steps):
    journal = StateJournal(require_signatures=False)
    runtime = RuntimeEngine(
        max_actions=4,
        state_journal=journal,
        runtime_id="plan-binding-runtime",
    )
    observed = []

    result = runtime.execute(
        Intent("run a bounded plan", "principal-1"),
        steps,
        executor=lambda envelope: observed.append(envelope) or envelope.step_id,
        verifier=lambda envelope, output: output == envelope.step_id,
        execution_id="execution-1",
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    entries = {entry.step_id: entry for entry in journal.snapshot()}
    envelopes = {item.step_id: item for item in observed}
    return entries, envelopes


def _steps(*, dependency: bool):
    return (
        PlanStep("step-a", "prepare", "compute", "normal", ()),
        PlanStep(
            "step-b", "execute", "compute", "normal",
            ("step-a",) if dependency else (),
        ),
    )


def test_plan_digest_is_bound_to_step_attestation_digest():
    dependent_entries, dependent_envelopes = _execute(_steps(dependency=True))
    independent_entries, independent_envelopes = _execute(_steps(dependency=False))

    assert dependent_envelopes["step-b"].plan_digest != independent_envelopes["step-b"].plan_digest
    assert dependent_entries["step-b"].action_digest != independent_entries["step-b"].action_digest


def test_plan_digest_is_stable_under_input_order_permutation():
    steps = _steps(dependency=True)
    forward_entries, forward_envelopes = _execute(steps)
    reverse_entries, reverse_envelopes = _execute(tuple(reversed(steps)))

    assert forward_envelopes["step-b"].plan_digest == reverse_envelopes["step-b"].plan_digest
    # The action digest also includes a fresh nonce, so only the plan binding is stable.
    assert forward_entries["step-b"].action_digest != reverse_entries["step-b"].action_digest


def test_plan_digest_is_present_on_every_dispatched_step():
    _, envelopes = _execute(_steps(dependency=True))
    assert all(len(envelope.plan_digest) == 64 for envelope in envelopes.values())


def test_noncanonical_plan_is_rejected_before_dispatch():
    journal = StateJournal(require_signatures=False)
    runtime = RuntimeEngine(max_actions=1, state_journal=journal)
    dispatched = []
    result = runtime.execute(
        Intent("reject malformed plan", "principal-1"),
        (PlanStep("step-a", "unsafe serialization", parameters={"opaque": object()}),),
        executor=lambda envelope: dispatched.append(envelope),
        verifier=lambda envelope, output: True,
        execution_id="execution-invalid",
    )
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "plan_digest_invalid"
    assert dispatched == []
    assert journal.snapshot() == ()
