from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace

from core.contracts import TaskSpec
from core.limits import RuntimeLimits
from core.operational_runtime import OperationalNORYXRuntime
from core.user_understanding import UnderstandingConsent, UserUnderstandingEngine
from gateway.runtime_adapter import RuntimeAdapter
from noryx7_runtime.model_fabric import ModelFabric


class ClosureModel:
    name = "closure-model"
    capabilities = frozenset({"text", "chat", "reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        if "Begin the response with exactly APPROVE or REJECT" in prompt:
            return "APPROVE: independent review completed."
        if "Reconcile the Primary proposal with the Secondary critique" in prompt:
            return "RECONCILED: canonical end-to-end closure verified."
        return "PRIMARY PROPOSAL: canonical end-to-end closure verified."


class EndToEndSystemClosureTests(unittest.TestCase):
    def _runtime(self):
        engine = UserUnderstandingEngine(
            consent=UnderstandingConsent.PRE_INTERACTION,
        )
        fabric = ModelFabric(
            [ClosureModel()],
            runtime_id="canonical-closure-runtime",
        )
        return OperationalNORYXRuntime(
            limits=RuntimeLimits(max_task_seconds=30.0),
            model_fabric=fabric,
            user_understanding=engine,
        )

    def test_direct_runtime_uses_one_canonical_system_fabric_and_records_lifecycle(self):
        runtime = self._runtime()
        try:
            task = TaskSpec(
                task_id="closure-runtime-task",
                task_type="conversation",
                objective="Verify canonical lifecycle provenance.",
                input="Verify the canonical NORYX7 runtime lifecycle.",
                constraints={},
                verification_requirements=("agent_result",),
                risk_class="normal",
                execution_id="closure-runtime-exec",
            )

            result = runtime.run_hypersynth(task)

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["verification"].valid)
            self.assertEqual(result["orchestration_stage"], "committed")

            events = runtime.audit.snapshot()
            names = {event.get("event") for event in events}
            self.assertIn("canonical_system_execution_received", names)
            self.assertIn("canonical_system_execution_committed", names)

            records = runtime.system_fabric.memory.snapshot()
            phases = {record.record_id.rsplit(":", 1)[-1] for record in records}
            self.assertIn("runtime_received", phases)
            self.assertIn("runtime_committed", phases)
        finally:
            runtime.shutdown_agents()

    def test_gateway_adapter_shares_runtime_fabric_and_closes_gateway_lifecycle(self):
        runtime = self._runtime()
        try:
            adapter = RuntimeAdapter(runtime)
            execution_id = "closure-gateway-exec"

            result = adapter.execute(
                client_id="closure-web-client",
                text="Verify the gateway to runtime closure.",
                execution_id=execution_id,
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["verification"]["valid"])

            records = runtime.system_fabric.memory.snapshot()
            record_ids = {record.record_id for record in records}
            self.assertIn(f"execution:{execution_id}:gateway_received", record_ids)
            self.assertIn(f"execution:{execution_id}:runtime_received", record_ids)
            self.assertIn(f"execution:{execution_id}:runtime_committed", record_ids)
            self.assertIn(f"execution:{execution_id}:gateway_completed", record_ids)
        finally:
            runtime.shutdown_agents()


if __name__ == "__main__":
    unittest.main()
