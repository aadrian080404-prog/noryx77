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
            raise SystemExit(
                f"PATCH ABORTED: {path}: expected 1 match, found {count}: {old[:180]!r}"
            )
        text = text.replace(old, new, 1)
        print(f"PATCHED BLOCK: {path}")
    if text == original:
        print(f"NO NEW CHANGES: {path}")
        return
    target.write_text(text, encoding="utf-8")
    print(f"UPDATED: {path}")


patch("core/agents.py", [
    (
        "    def run(self, task: TaskSpec) -> AgentResult:\n        raise NotImplementedError\n",
        "    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:\n        raise NotImplementedError\n",
    ),
    (
        "    def run(self, task: TaskSpec) -> AgentResult:\n        check = self.verifier.verify_task(task)\n",
        "    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:\n        check = self.verifier.verify_task(task)\n",
    ),
])

patch("core/llm/agent.py", [
    (
        "    def _build_prompt(self, task: TaskSpec) -> str:\n",
        "    def _build_prompt(self, task: TaskSpec, interaction_context=None) -> str:\n",
    ),
    (
        "            f\"User input: {task.input!r}\\n\"\n        )\n\n    def _generate",
        "            f\"User input: {task.input!r}\\n\"\n            + (\n                \"=== USER INTERACTION CONTEXT ===\\n\"\n                + interaction_context.as_prompt_context()\n                + \"\\n=== END USER INTERACTION CONTEXT ===\\n\"\n                if interaction_context is not None\n                else \"\"\n            )\n        )\n\n    def _generate",
    ),
    (
        "    def run(self, task: TaskSpec) -> AgentResult:\n        check = self.verifier.verify_task(task)\n",
        "    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:\n        check = self.verifier.verify_task(task)\n",
    ),
    (
        "        prompt = self._build_prompt(task)\n",
        "        prompt = self._build_prompt(task, interaction_context=interaction_context)\n",
    ),
])

patch("core/hypersynth.py", [
    (
        "    def run(self, task: TaskSpec, *, deadline_check=None, preferred_agent=None):\n",
        "    def run(self, task: TaskSpec, *, deadline_check=None, preferred_agent=None, interaction_context=None):\n",
    ),
    (
        "                else:\n                        decision, result = operation()\n",
        "                else:\n                        decision, result = operation()\n",
    ),
    (
        "                    if self.recovery is not None:\n                        decision, result = self.recovery.run_if_normal(operation, expected_epoch=recovery_epoch)\n                    else:\n                        decision, result = operation()\n",
        "                    if self.recovery is not None:\n                        decision, result = self.recovery.run_if_normal(operation, expected_epoch=recovery_epoch)\n                    else:\n                        decision, result = operation()\n",
    ),
    (
        "                    operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child), calls_used=index, execution_id=task.execution_id)\n",
        "                    operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child, interaction_context=interaction_context), calls_used=index, execution_id=task.execution_id)\n",
    ),
])

patch("core/hypersynth_runtime.py", [
    (
        "            result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded)\n",
        "            result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent, interaction_context=interaction_context) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded, interaction_context=interaction_context)\n",
    ),
])

print("INTERACTION CONTEXT AGENT PROPAGATION = APPLIED")
print("LLM PROMPT CONTEXT = WIRED")
print("DETERMINISTIC AGENT COMPATIBILITY = PRESERVED")
