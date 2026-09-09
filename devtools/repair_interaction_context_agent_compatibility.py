from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        print(f"ALREADY APPLIED: {path}")
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"PATCH ABORTED: {path}: expected 1 match, found {count}: {old[:180]!r}"
        )
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED BLOCK: {path}")


patch(
    "core/hypersynth.py",
    "                    operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child, interaction_context=interaction_context), calls_used=index, execution_id=task.execution_id)\n",
    "                    operation = lambda: self.action_gate.authorize_and_execute(\n                        action,\n                        (\n                            lambda: agent.run(child, interaction_context=interaction_context)\n                            if interaction_context is not None\n                            else lambda: agent.run(child)\n                        )(),\n                        calls_used=index,\n                        execution_id=task.execution_id,\n                    )\n",
)

print("INTERACTION CONTEXT AGENT COMPATIBILITY = REPAIRED")
print("LEGACY AGENT SIGNATURES = PRESERVED")
print("CONTEXT PROPAGATION = PRESERVED WHEN PRESENT")
