import unittest

from .context import ContextManager
from .contracts import TaskSpec
from .memory import MemoryItem, MemoryStore
from .planning import Plan, PlanStep, Planner


class PlanningContextTests(unittest.TestCase):
    def test_planner_binds_verified_context(self):
        memory = MemoryStore()
        memory.put(MemoryItem("m1", "prior", source="task-1", importance=1.0))
        context = ContextManager(memory=memory).build("task-1", {"input": "x"}, source_ids=("task-1",))
        task = TaskSpec("task-1", "analysis", "answer", {})
        plan = Planner().build(task, context)

        self.assertEqual(plan.context_version, context.version)
        self.assertEqual(plan.context_source_ids, context.source_ids)
        self.assertTrue(Planner().verify(plan, task, context).valid)

    def test_planner_rejects_foreign_context(self):
        context = ContextManager().build("other-task")
        task = TaskSpec("task-2", "analysis", "answer", {})
        with self.assertRaisesRegex(ValueError, "context_task_mismatch"):
            Planner().build(task, context)

    def test_verifier_rejects_plan_bound_to_different_context(self):
        manager = ContextManager()
        context_a = manager.build("task-3", source_ids=("task-3",))
        context_b = manager.build("task-3", source_ids=("task-3",))
        task = TaskSpec("task-3", "analysis", "answer", {})
        plan = Planner().build(task, context_a)

        check = Planner().verify(plan, task, context_b)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_context_mismatch")

    def test_legacy_planner_contract_remains_unbound_without_context(self):
        task = TaskSpec("task-4", "analysis", "answer", {})
        plan = Planner().build(task)
        self.assertIsNone(plan.context_version)
        self.assertEqual(plan.context_source_ids, ())
        self.assertTrue(Planner().verify(plan, task).valid)

    def test_context_source_reordering_invalidates_plan_binding(self):
        manager = ContextManager()
        context = manager.build("task-5", source_ids=("task-5", "memory-a"))
        task = TaskSpec("task-5", "analysis", "answer", {})
        plan = Plan(task.task_id, (PlanStep("task-5:0", task.objective, risk_class=task.risk_class),), context.version, ("task-5", "memory-b"))

        check = Planner().verify(plan, task, context)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_context_mismatch")


if __name__ == "__main__":
    unittest.main()
