import unittest

from noryx7_runtime.model_fabric import ModelFabric

from .contracts import TaskSpec
from .hypersynth import Hypersynth
from .planning import PlanStep
from .provenance import ProvenanceContext, seal_provenance, verify_provenance
from .verification import VerificationEngine
from .router import ResourceRouter


class CountingModel:
    name = "counting"
    capabilities = frozenset({"reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, *, tools=()):
        self.calls += 1
        return f"answer:{prompt}"


class HypersynthModelFabricProvenanceTests(unittest.TestCase):
    def test_model_fabric_executes_once_and_provenance_binds_that_result(self):
        model = CountingModel()
        runtime_id = "runtime-1"
        fabric = ModelFabric([model], runtime_id=runtime_id, binding_key=b"f" * 32)
        kernel = Hypersynth(
            VerificationEngine(),
            ResourceRouter(),
            runtime_id=runtime_id,
            provenance_key=b"p" * 32,
            model_fabric=fabric,
        )
        task = TaskSpec(
            "task-1", "research", "analyze", "input",
            {"principal_id": "principal-1", "runtime_id": runtime_id},
            execution_id="exec-1",
        )
        step = PlanStep("step-1", "analyze", "compute", "normal")
        agent, request = kernel._model_agent(task, step)
        child = TaskSpec("step-1", "research", "analyze", "input", task.constraints, (), "normal", "exec-1")

        result = agent.run(child)

        self.assertEqual(model.calls, 1)
        self.assertEqual(result.output, "answer:analyze")
        self.assertIsNotNone(agent.last_fabric_result)
        self.assertTrue(fabric.verify_result(request, agent.last_fabric_result))

        provenance = kernel._provenance_start(task, "route")
        provenance = provenance.bind_model(agent.last_fabric_result.request_digest, agent.last_fabric_result)
        seal = seal_provenance(provenance, kernel.provenance_key)
        self.assertTrue(verify_provenance(provenance, seal, kernel.provenance_key))
        self.assertEqual(provenance.model_request_digest, agent.last_fabric_result.request_digest)
        self.assertEqual(len(provenance.model_result_digest), 64)

    def test_model_fabric_constraints_omit_optional_limits_without_synthetic_zero_latency(self):
        model = CountingModel()
        fabric = ModelFabric([model], runtime_id="runtime-1", binding_key=b"f" * 32)
        kernel = Hypersynth(VerificationEngine(), ResourceRouter(), runtime_id="runtime-1", model_fabric=fabric)
        task = TaskSpec("task-1", "research", "analyze", "input", {"runtime_id": "runtime-1"}, execution_id="exec-1")
        step = PlanStep("step-1", "analyze", "compute", "normal")

        agent, request = kernel._model_agent(task, step)

        self.assertIsNotNone(agent)
        self.assertIsNone(request.max_latency_ms)
        self.assertIsNone(request.max_cost)

    def test_invalid_model_limits_fail_closed_before_execution(self):
        model = CountingModel()
        fabric = ModelFabric([model], runtime_id="runtime-1", binding_key=b"f" * 32)
        kernel = Hypersynth(VerificationEngine(), ResourceRouter(), runtime_id="runtime-1", model_fabric=fabric)
        task = TaskSpec("task-1", "research", "analyze", "input", {"runtime_id": "runtime-1", "max_latency_ms": 0}, execution_id="exec-1")
        step = PlanStep("step-1", "analyze", "compute", "normal")

        with self.assertRaises(ValueError):
            kernel._model_agent(task, step)
        self.assertEqual(model.calls, 0)


if __name__ == "__main__":
    unittest.main()
