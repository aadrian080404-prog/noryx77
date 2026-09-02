import unittest

from .context import ContextManager
from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime
from .memory import MemoryItem, MemoryStore


class ContextMemoryTests(unittest.TestCase):
    def test_attached_memory_is_retrieved_only_for_task_provenance(self):
        memory = MemoryStore()
        memory.put(MemoryItem("unrelated", "do not leak", source="other-task", importance=1.0))
        memory.put(MemoryItem("low", "old", source="task-1", importance=0.2))
        memory.put(MemoryItem("high", "relevant", source="task-1", importance=0.9))
        context = ContextManager(memory=memory, memory_limit=2).build("task-1", {"input": "x"}, source_ids=("task-1",))

        self.assertEqual(tuple(item.memory_id for item in context.values["memory"]), ("high", "low"))
        self.assertEqual(context.source_ids, ("task-1", "high", "low"))
        self.assertEqual(context.values["input"], "x")

    def test_context_snapshot_isolated_from_memory_mutation(self):
        memory = MemoryStore()
        memory.put(MemoryItem("m1", {"nested": [1]}, source="task-2", importance=1.0))
        context = ContextManager(memory=memory).build("task-2")
        context.values["memory"][0].content["nested"].append(2)

        stored = memory.get("m1")
        self.assertEqual(stored.content, {"nested": [1]})

    def test_memory_integrity_failure_propagates_fail_closed(self):
        memory = MemoryStore()
        memory.put(MemoryItem("m1", "trusted", source="task-3", importance=1.0))
        memory._items["m1"] = MemoryItem("m1", "tampered", source="task-3", importance=1.0)
        manager = ContextManager(memory=memory)

        with self.assertRaisesRegex(MemoryError, "memory_integrity_failure"):
            manager.build("task-3")

    def test_attach_memory_rejects_non_retrievable_object(self):
        manager = ContextManager()
        with self.assertRaisesRegex(TypeError, "memory_retrieve_required"):
            manager.attach_memory(object())

    def test_runtime_wires_shared_memory_into_kernel_context(self):
        memory = MemoryStore()
        memory.put(MemoryItem("prior", "previous result", source="task-runtime", importance=1.0))
        runtime = HypersynthRuntime(memory=memory)
        task = TaskSpec("task-runtime", "analysis", "answer", {})
        result = runtime.run(task)

        self.assertEqual(result["status"], "completed")
        context = result["context"]
        self.assertEqual(tuple(item.memory_id for item in context.values["memory"]), ("prior",))
        self.assertEqual(context.source_ids, ("task-runtime", "prior"))


if __name__ == "__main__":
    unittest.main()
