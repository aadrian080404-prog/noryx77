import unittest

from .actions import ActionGate
from .agents import DeterministicAgent
from .contracts import TaskSpec
from .hypersynth import Hypersynth
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine
from .provenance import ProvenanceContext, seal_provenance, verify_provenance


class HypersynthProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        self.memory = MemoryStore()
        self.key = b"p" * 32
        self.kernel = Hypersynth(
            self.verifier,
            self.router,
            action_gate=gate,
            memory=self.memory,
            provenance_key=self.key,
            runtime_id="runtime-A",
        )

    def task(self, **kwargs):
        values = dict(
            task_id="prov-task",
            task_type="research",
            objective="analyze",
            input="data",
            risk_class="normal",
            execution_id="execution-A",
            constraints={"principal_id": "principal-A"},
        )
        values.update(kwargs)
        return TaskSpec(**values)

    def test_completed_run_contains_sealed_provenance(self):
        result = self.kernel.run(self.task())
        self.assertEqual(result["status"], "completed")
        context = result["provenance"]
        seal = result["provenance_seal"]
        self.assertTrue(verify_provenance(context, seal, self.key))
        self.assertEqual(context.runtime_id, "runtime-A")
        self.assertEqual(context.execution_id, "execution-A")
        self.assertEqual(context.principal_id, "principal-A")
        self.assertEqual(context.result_digest, result["provenance"].result_digest)

    def test_execution_swap_invalidates_provenance(self):
        result = self.kernel.run(self.task())
        context = result["provenance"]
        forged = ProvenanceContext(
            context.runtime_id,
            "execution-B",
            context.principal_id,
            context.memory_digest,
            context.route_digest,
            context.request_digest,
            context.result_digest,
        )
        self.assertFalse(verify_provenance(forged, result["provenance_seal"], self.key))

    def test_principal_swap_invalidates_provenance(self):
        result = self.kernel.run(self.task())
        context = result["provenance"]
        forged = ProvenanceContext(
            context.runtime_id,
            context.execution_id,
            "principal-B",
            context.memory_digest,
            context.route_digest,
            context.request_digest,
            context.result_digest,
        )
        self.assertFalse(verify_provenance(forged, result["provenance_seal"], self.key))

    def test_route_swap_invalidates_provenance(self):
        result = self.kernel.run(self.task())
        context = result["provenance"]
        forged = ProvenanceContext(
            context.runtime_id,
            context.execution_id,
            context.principal_id,
            context.memory_digest,
            "0" * 64,
            context.request_digest,
            context.result_digest,
        )
        self.assertFalse(verify_provenance(forged, result["provenance_seal"], self.key))

    def test_result_swap_invalidates_provenance(self):
        result = self.kernel.run(self.task())
        context = result["provenance"]
        forged = context.bind_result("attacker-output")
        self.assertFalse(verify_provenance(forged, result["provenance_seal"], self.key))

    def test_missing_principal_fails_closed_when_provenance_enabled(self):
        result = self.kernel.run(self.task(constraints={}))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "allocation")
        self.assertEqual(result["verification"].stage, "provenance")
        self.assertEqual(result["verification"].reason, "missing_provenance_principal")

    def test_cross_runtime_keyed_kernel_cannot_accept_transplanted_seal(self):
        result = self.kernel.run(self.task())
        context = result["provenance"]
        other = ProvenanceContext(
            "runtime-B",
            context.execution_id,
            context.principal_id,
            context.memory_digest,
            context.route_digest,
            context.request_digest,
            context.result_digest,
        )
        self.assertFalse(verify_provenance(other, result["provenance_seal"], self.key))


if __name__ == "__main__":
    unittest.main()
