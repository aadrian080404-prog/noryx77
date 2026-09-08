from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, replacements: list[tuple[str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        if new in text:
            print(f"ALREADY APPLIED: {path}")
            continue
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"PATCH ABORTED: {path}: expected 1 match, found {count}: {old[:120]!r}")
        text = text.replace(old, new, 1)
        print(f"PATCHED BLOCK: {path}")
    if text == original:
        print(f"NO NEW CHANGES: {path}")
        return
    target.write_text(text, encoding="utf-8")
    print(f"UPDATED: {path}")


patch("core/hypersynth.py", [
    (
        "        self.context_manager = context_manager or ContextManager()\n",
        "        self.context_manager = context_manager or ContextManager(memory=memory)\n",
    ),
    (
        '        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))\n',
        '        context = self.context_manager.build(\n            task.task_id,\n            {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)},\n            source_ids=(task.task_id,),\n            execution_id=task.execution_id,\n        )\n',
    ),
    (
        '                    if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))\n',
        '                    if not decision.allowed:\n                        check = decision.verification\n                        if check.reason == "execution_failure":\n                            check = VerificationResult(False, "execution", "execution_failure")\n                        return self._reject("execution", task, check, results=tuple(results))\n',
    ),
    (
        '                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=task.task_id, importance=0.5, execution_id=task.execution_id))\n',
        '                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=task.task_id, importance=0.5, execution_id=task.execution_id))\n                execution_key = "execution:" + task.execution_id + ":final"\n                self.memory.put(MemoryItem(execution_key, final_output, kind="working", source=task.task_id, importance=0.7, execution_id=task.execution_id))\n',
    ),
])

print("ARCHITECTURE REPAIR = APPLIED")
print("CONTEXT EXECUTION ID = WIRED")
print("ACTION EXECUTION FAILURE = NORMALIZED")
print("EXECUTION MEMORY INDEX = WRITTEN")
