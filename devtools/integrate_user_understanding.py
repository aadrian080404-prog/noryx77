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
            raise SystemExit(f"PATCH ABORTED: {path}: expected 1 match, found {count}: {old[:160]!r}")
        text = text.replace(old, new, 1)
        print(f"PATCHED BLOCK: {path}")
    if text == original:
        print(f"NO NEW CHANGES: {path}")
        return
    target.write_text(text, encoding="utf-8")
    print(f"UPDATED: {path}")


patch("core/runtime.py", [
    (
        "from .interaction_context import InteractionContext\n",
        "from .interaction_context import InteractionContext, build_interaction_context\nfrom .user_understanding import UnderstandingConsent, UserContent, UserUnderstandingEngine\n",
    ),
    (
        "        model_fabric=None,\n    ):\n",
        "        model_fabric=None,\n        user_understanding: UserUnderstandingEngine | None = None,\n    ):\n",
    ),
    (
        "        self._model_fabric = model_fabric\n",
        "        self._model_fabric = model_fabric\n        if user_understanding is not None and not isinstance(user_understanding, UserUnderstandingEngine):\n            raise TypeError(\"invalid_user_understanding_engine\")\n        self.user_understanding = user_understanding\n",
    ),
    (
        "    def run_hypersynth(\n        self,\n        task: TaskSpec,\n        interaction_context: InteractionContext | None = None,\n    ):\n",
        "    def run_hypersynth(\n        self,\n        task: TaskSpec,\n        interaction_context: InteractionContext | None = None,\n    ):\n",
    ),
    (
        "        task_id = getattr(task, \"task_id\", None)\n        envelope = None\n\n        try:\n            envelope = self._context_envelope(\n",
        "        task_id = getattr(task, \"task_id\", None)\n        envelope = None\n\n        try:\n            if interaction_context is None and self.user_understanding is not None:\n                content = UserContent(\n                    content_id=task_id or execution_id,\n                    text=str(getattr(task, \"input\", \"\")),\n                    source=\"runtime_task_input\",\n                )\n                profile = self.user_understanding.build_profile((content,))\n                interaction_context = build_interaction_context(profile)\n                self.audit.record(\n                    \"user_understanding_derived\",\n                    task_id=task_id,\n                    execution_id=execution_id,\n                    profile_id=profile.profile_id,\n                    context_id=interaction_context.context_id,\n                    consent=self.user_understanding.consent.value,\n                )\n            envelope = self._context_envelope(\n",
    ),
])

print("USER UNDERSTANDING INTEGRATION = APPLIED")
print("CONSENT BOUNDARY = PRESERVED")
print("INTERACTION CONTEXT = CANONICAL RUNTIME INPUT")
