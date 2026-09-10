from __future__ import annotations

import time

from core.agent_continuity import AgentContinuityScheduler
from core.scientific_knowledge import ResearchExperiment, ResearchSource, ScientificKnowledgeFabric


class _Runtime:
    online = True

    def __init__(self):
        self.cycles = []

    def heartbeat(self):
        class Status:
            def __init__(self, agent_id):
                self.agent_id = agent_id
                self.state = "ONLINE"
        return (Status("primary"), Status("secondary"))


def test_scientific_knowledge_requires_authorized_sources_and_verified_experiments():
    fabric = ScientificKnowledgeFabric()
    source = ResearchSource(
        source_id="paper-1",
        title="Example scientific paper",
        discipline="physics",
        source_type="metadata",
        uri="https://example.invalid/paper-1",
        access_status="metadata_only",
    )
    fabric.add_source(source)
    hypothesis = fabric.formulate_hypothesis(
        hypothesis_id="hyp-1",
        statement="The measured relation is stable under the stated conditions.",
        source_ids=("paper-1",),
        confidence=0.6,
        falsifiers=("measurement_error_exceeds_threshold",),
        experiment_plan=("repeat_measurement", "compare_residuals"),
    )
    assert hypothesis.is_well_formed()
    try:
        fabric.admit_experiment(ResearchExperiment("exp-bad", "hyp-1", "test", "digest", "", False))
    except PermissionError as exc:
        assert str(exc) == "unverified_experiment_result"
    else:
        raise AssertionError("unverified experiment was admitted")
    admitted = fabric.admit_experiment(ResearchExperiment("exp-1", "hyp-1", "test", "digest", "verified", True))
    assert admitted.verified is True


def test_continuity_scheduler_runs_bounded_cycles_and_stops():
    runtime = _Runtime()
    seen = []
    scheduler = AgentContinuityScheduler(
        agent_runtime=runtime,
        cycle_callback=seen.append,
        interval_seconds=0.01,
        max_cycles_per_start=2,
    )
    scheduler.start()
    deadline = time.time() + 1.0
    while scheduler.running and time.time() < deadline:
        time.sleep(0.01)
    scheduler.stop()
    status = scheduler.status()
    assert status.running is False
    assert status.cycles == 2
    assert len(seen) == 2
    assert all(item.objective == "bounded_self_evaluation_and_cross_agent_exercise" for item in seen)
