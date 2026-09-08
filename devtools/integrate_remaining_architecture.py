from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path, replacements):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"PATCH ABORTED: {path}: expected 1 match, found {count}: {old[:100]!r}")
        text = text.replace(old, new)
    if text == original:
        raise SystemExit(f"PATCH ABORTED: {path}: no changes")
    target.write_text(text, encoding="utf-8")
    print(f"PATCHED: {path}")


patch("core/context.py", [
    (
        'class ContextManager:\n    """Creates context snapshots isolated from caller-owned mutable data."""\n    def __init__(self):\n        self._versions = {}\n',
        'class ContextManager:\n    """Creates isolated context snapshots and optionally hydrates prior task memory."""\n    def __init__(self, memory=None):\n        self._versions = {}\n        self.memory = memory\n\n    def _memory_values(self, task_id, limit=16):\n        if self.memory is None:\n            return ()\n        try:\n            items = self.memory.list()\n        except Exception:\n            return ()\n        matches = [item for item in items if item.source == task_id]\n        matches.sort(key=lambda item: (-float(item.importance), item.memory_id))\n        return tuple({\n            "memory_id": item.memory_id,\n            "kind": item.kind,\n            "content": deepcopy(item.content),\n            "execution_id": item.execution_id,\n        } for item in matches[:limit])\n\n    def build(self, task_id, values=None, source_ids=(), *, execution_id=None):\n        if not isinstance(task_id, str) or not task_id.strip():\n            raise ValueError("task_id required")\n        if values is not None and not isinstance(values, dict):\n            raise ValueError("values must be a dict")\n        if not isinstance(source_ids, tuple):\n            raise ValueError("source_ids must be a tuple")\n        if any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):\n            raise ValueError("source_ids must contain non-empty strings")\n        if execution_id is not None and (not isinstance(execution_id, str) or not execution_id.strip()):\n            raise ValueError("execution_id must be a non-empty string when provided")\n        version = self._versions.get(task_id, 0) + 1\n        self._versions[task_id] = version\n        hydrated = deepcopy(values or {})\n        prior_memory = self._memory_values(task_id)\n        if prior_memory:\n            hydrated["memory"] = prior_memory\n        return ContextSnapshot(task_id, hydrated, tuple(source_ids), version)\n',
    ),
])

patch("core/hypersynth.py", [
    (
        'self.context_manager = context_manager or ContextManager()\n',
        'self.context_manager = context_manager or ContextManager(memory=memory)\n',
    ),
    (
        'context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))\n',
        'context = self.context_manager.build(\n            task.task_id,\n            {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)},\n            source_ids=(task.task_id,),\n            execution_id=task.execution_id,\n        )\n',
    ),
])

patch("core/hypersynth.py", [
    (
        'memory_key = "task:" + task.execution_id + ":" + task.task_id\n                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=task.task_id, importance=0.5, execution_id=task.execution_id))\n',
        'memory_key = "task:" + task.execution_id + ":" + task.task_id\n                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=task.task_id, importance=0.5, execution_id=task.execution_id))\n                execution_key = "execution:" + task.execution_id + ":final"\n                self.memory.put(MemoryItem(execution_key, final_output, kind="working", source=task.task_id, importance=0.7, execution_id=task.execution_id))\n',
    ),
])

print("SINGLE-PASS ARCHITECTURE INTEGRATION = APPLIED")
print("MEMORY -> CONTEXT -> HYPERSYNTH = WIRED")
print("MEMORY PROVENANCE = PRESERVED")
