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
    "from uuid import uuid4\n",
    "from uuid import uuid4\nimport inspect\n",
)

patch(
    "core/hypersynth.py",
    "                    if interaction_context is None:\n                        operation = lambda: self.action_gate.authorize_and_execute(\n                            action,\n                            lambda: agent.run(child),\n                            calls_used=index,\n                            execution_id=task.execution_id,\n                        )\n                    else:\n                        operation = lambda: self.action_gate.authorize_and_execute(\n                            action,\n                            lambda: agent.run(child, interaction_context=interaction_context),\n                            calls_used=index,\n                            execution_id=task.execution_id,\n                        )\n",
    "                    run_parameters = inspect.signature(agent.run).parameters\n                    accepts_context = (\n                        \"interaction_context\" in run_parameters\n                        or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in run_parameters.values())\n                    )\n                    if interaction_context is not None and accepts_context:\n                        operation = lambda: self.action_gate.authorize_and_execute(\n                            action,\n                            lambda: agent.run(child, interaction_context=interaction_context),\n                            calls_used=index,\n                            execution_id=task.execution_id,\n                        )\n                    else:\n                        operation = lambda: self.action_gate.authorize_and_execute(\n                            action,\n                            lambda: agent.run(child),\n                            calls_used=index,\n                            execution_id=task.execution_id,\n                        )\n",
)

patch(
    "core/hypersynth_runtime.py",
    "import hashlib\nimport time\n",
    "import hashlib\nimport inspect\nimport time\n",
)

patch(
    "core/hypersynth_runtime.py",
    "            result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent, interaction_context=interaction_context) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded, interaction_context=interaction_context)\n",
    "            kernel_parameters = inspect.signature(self.kernel.run).parameters\n            kernel_accepts_context = (\n                \"interaction_context\" in kernel_parameters\n                or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in kernel_parameters.values())\n            )\n            if kernel_accepts_context:\n                result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent, interaction_context=interaction_context) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded, interaction_context=interaction_context)\n            else:\n                result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded)\n",
)

print("INTERACTION CONTEXT AGENT COMPATIBILITY = REPAIRED")
print("LEGACY AGENT SIGNATURES = PRESERVED")
print("LEGACY KERNEL SIGNATURES = PRESERVED")
print("CONTEXT PROPAGATION = PRESERVED WHEN SUPPORTED")
