import unittest

from .agents import ProviderAgent
from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime
from .provider import CallableProvider, ProviderRequest
from .router import ResourceRouter


class AllocationAdversarialTests(unittest.TestCase):
    def test_allocation_must_not_depend_on_agent_id_order_when_capacity_differs(self):
        calls = []

        def execute(request: ProviderRequest):
            calls.append(request.task_id)
            return "ok"

        router = ResourceRouter()
        # Lexicographically first on purpose: it is underpowered for research.
        router.register(
            ProviderAgent(
                "a-underpowered",
                CallableProvider(execute, provider_id="p-small"),
                model_class="medium",
            )
        )
        router.register(
            ProviderAgent(
                "z-sufficient",
                CallableProvider(execute, provider_id="p-large"),
                model_class="large",
            )
        )

        runtime = HypersynthRuntime(router=router)
        task = TaskSpec("allocation-order-attack", "research", "research objective", "input")
        result = runtime.run(task)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["results"][-1].agent_id, "z-sufficient")
        self.assertEqual(calls, ["allocation-order-attack:0"])


if __name__ == "__main__":
    unittest.main()
