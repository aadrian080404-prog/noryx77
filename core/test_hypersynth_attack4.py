import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep, Planner
from .reasoning import InternalSimulator, SimulationResult
from .router import ResourceRouter
from .agents import DeterministicAgent
from .verification import VerificationEngine


class ExplodingSimulator(InternalSimulator):
    def simulate(self, task, hypotheses):
        raise RuntimeError("injected simulator failure")


class TwoStepPlanner(Planner):
    def build(self, task, context=None):
        version = None if context is None else context.version
        sources = () if context is None else context.source_ids
        return Plan(task.task_id, (
            PlanStep(task.task_id + ":0", task.objective, "compute", task.risk_class),
            PlanStep(task.task_id + ":1", task.objective, "compute", task.risk_class),
        ), version, sources)


class PartialFailureAgent(DeterministicAgent):
    def __init__(self, verifier, fail_on):
        super().__init__(verifier)
        self.fail_on = fail_on
        self.calls = 0

    def run(self, task):
        self.calls += 1
        if self.calls == self.fail_on:
            raise RuntimeError("injected execution failure")
        return super().run(task)


class ForgedResultAgent(DeterministicAgent):
    def run(self, task):
        return AgentResult(self.agent_id, "forged-task", "completed", "forged", VerificationResult(True, "result", "forged"))


class ForgedSimulation(InternalSimulator):
    def simulate(self, task, hypotheses):
        return tuple(SimulationResult("forged", True, "feasible") for _ in hypotheses)


class Attack4Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack4", "research", "objective", "input", risk_class="normal")

    def router(self, agent):
        router = ResourceRouter()
        router.register(agent)
        return router

    def test_simulator_exception_fails_closed_before_allocation(self):
        verifier = VerificationEngine()
        kernel = Hypersynth(verifier, self.router(DeterministicAgent(verifier)), simulator=ExplodingSimulator())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "simulation_failure")

    def test_partial_execution_failure_never_reports_success(self):
        verifier = VerificationEngine()
        agent = PartialFailureAgent(verifier, fail_on=2)
        kernel = Hypersynth(verifier, self.router(agent), planner=TwoStepPlanner(max_steps=2), max_steps=2, max_agents=2)
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "agent_execution_failure")
        self.assertEqual(len(result["results"]), 1)

    def test_forged_agent_result_cannot_override_identity(self):
        verifier = VerificationEngine()
        agent = ForgedResultAgent(verifier)
        kernel = Hypersynth(verifier, self.router(agent))
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "task_id_mismatch")

    def test_simulation_ids_are_bound_to_hypotheses(self):
        verifier = VerificationEngine()
        kernel = Hypersynth(verifier, self.router(DeterministicAgent(verifier)), simulator=ForgedSimulation())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "simulation_hypothesis_id_mismatch")


if __name__ == "__main__":
    unittest.main()
