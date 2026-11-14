from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HYPERSYNTH_RUNTIME = ROOT / "core" / "hypersynth_runtime.py"
HYPERSYNTH = ROOT / "core" / "hypersynth.py"
TEST = ROOT / "core" / "test_memory_context_integration.py"


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f"patch anchor not found: {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


# Memory becomes an actual context input, while remaining execution-isolated and bounded.
replace_once(
    HYPERSYNTH_RUNTIME,
    'from .memory import MemoryStore\n',
    'from .memory import MemoryItem, MemoryStore\n',
)
replace_once(
    HYPERSYNTH_RUNTIME,
    '        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)\n',
    '        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)\n        self.context_manager = MemoryContextManager(self.memory)\n',
)
replace_once(
    HYPERSYNTH_RUNTIME,
    'from .frontier_capabilities import install_frontier_capabilities\n',
    'from .frontier_capabilities import install_frontier_capabilities\n\n\nclass MemoryContextManager:\n    """Builds bounded HYPERSYNTH context from execution-scoped memory."""\n\n    MAX_ITEMS = 8\n\n    def __init__(self, memory: MemoryStore):\n        if not isinstance(memory, MemoryStore):\n            raise TypeError("memory_store_required")\n        self.memory = memory\n\n    def build(self, task_id, values, source_ids=()):\n        execution_id = values.get("execution_id", "") if isinstance(values, dict) else ""\n        items = self.memory.list(execution_id=execution_id) if execution_id else ()\n        bounded = tuple(items[-self.MAX_ITEMS:])\n        merged = dict(values) if isinstance(values, dict) else {"value": values}\n        merged["memory"] = tuple(\n            {\n                "memory_id": item.memory_id,\n                "kind": item.kind,\n                "source": item.source,\n                "importance": item.importance,\n                "content": item.content,\n            }\n            for item in bounded\n        )\n        return ContextManager().build(task_id, merged, source_ids=tuple(source_ids))\n',
)
replace_once(
    HYPERSYNTH_RUNTIME,
    '        self.kernel = Hypersynth(\n            self.verifier, self.router, planner=planner, action_gate=self.action_gate,\n            memory=self.memory, audit=self.audit, max_steps=self.limits.max_actions_per_task,\n',
    '        self.kernel = Hypersynth(\n            self.verifier, self.router, planner=planner, action_gate=self.action_gate,\n            memory=self.memory, context_manager=self.context_manager, audit=self.audit, max_steps=self.limits.max_actions_per_task,\n',
)
replace_once(
    HYPERSYNTH_RUNTIME,
    'from .contracts import TaskSpec, VerificationResult\n',
    'from .contracts import TaskSpec, VerificationResult\nfrom .context import ContextManager\n',
)

# Ensure the kernel context carries execution identity so retrieval is isolated by execution.
replace_once(
    HYPERSYNTH,
    '        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))\n',
    '        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks), "execution_id": task.execution_id}, source_ids=(task.task_id,))\n',
)

TEST.write_text(
    '''from core.context import ContextManager\nfrom core.contracts import TaskSpec\nfrom core.hypersynth_runtime import HypersynthRuntime\nfrom core.memory import MemoryItem, MemoryStore\n\n\ndef test_memory_context_is_execution_scoped_and_bounded():\n    memory = MemoryStore(max_items=20)\n    for index in range(10):\n        memory.put(MemoryItem(f"m-{index}", f"value-{index}", execution_id="exec-a"))\n    memory.put(MemoryItem("other", "secret", execution_id="exec-b"))\n    runtime = HypersynthRuntime(memory=memory)\n    task = TaskSpec("task-a", "research", "inspect", "input", {}, (), "normal", "exec-a")\n    context = runtime.context_manager.build(task.task_id, {"execution_id": task.execution_id}, source_ids=(task.task_id,))\n    prompt_context = context.as_prompt_context()\n    assert "value-9" in prompt_context\n    assert "value-2" not in prompt_context\n    assert "secret" not in prompt_context\n\n\ndef test_kernel_receives_memory_aware_context_manager():\n    runtime = HypersynthRuntime(memory=MemoryStore())\n    assert runtime.kernel.context_manager is runtime.context_manager\n''',
    encoding="utf-8",
)

print("MEMORY CONTEXT INTEGRATION PATCH = APPLIED")
