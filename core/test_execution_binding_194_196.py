import unittest

from .contracts import AgentResult, VerificationResult
from .router import ResourceRouter


class _Agent:
    agent_id = "a"
    model_class = "medium"
    capabilities = ()
    capacity_exempt = False

    def __init__(self, calls):
        self.calls = calls

    def run(self, task):
        self.calls.append("original")
        return AgentResult("a", task.task_id, "completed", "ok", VerificationResult(True, "result", "ok"))


class _Task:
    task_id = "t194"


class ExecutionBinding194To196Tests(unittest.TestCase):
    def test_attack_194_resolver_captures_bound_callable(self):
        calls = []
        router = ResourceRouter()
        agent = _Agent(calls)
        router.register(agent)
        bound = router.resolve_execution(agent)
        agent.run = lambda task: calls.append("replacement")
        result = bound(_Task())
        self.assertEqual(calls, ["original"])
        self.assertEqual(result.output, "ok")

    def test_attack_195_resolver_rejects_mutation_before_capture(self):
        router = ResourceRouter()
        agent = _Agent([])
        router.register(agent)
        agent.model_class = "large"
        with self.assertRaisesRegex(RuntimeError, "registered_agent_metadata_mutated"):
            router.resolve_execution(agent)

    def test_attack_196_resolver_rejects_replacement_object(self):
        router = ResourceRouter()
        registered = _Agent([])
        router.register(registered)
        replacement = _Agent([])
        with self.assertRaisesRegex(RuntimeError, "registered_agent_identity_changed"):
            router.resolve_execution(replacement)


if __name__ == "__main__":
    unittest.main()
