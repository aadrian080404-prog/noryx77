import os
import uuid

from noryx7_runtime.model_fabric import ModelFabric
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from core.llm import ModelFabricBridge, LLMBackedAgent
from core.contracts import TaskSpec

key = os.environ.get("OPENROUTER_API_KEY", "")
if not key.startswith("sk-or-v1-"):
    raise RuntimeError("OPENROUTER_API_KEY non configurata")

adapter = OpenRouterAdapter(
    model="openrouter/free",
    api_key=key,
    timeout_seconds=120.0,
)

fabric = ModelFabric(
    [adapter],
    runtime_id="noryx7-human-session",
)

print()
print("==========================================")
print("        NORYX7 — REAL LLM SESSION")
print("==========================================")
print("MODEL: openrouter/free")
print("FABRIC: ONLINE")
print("TOOLS: DISABLED")
print("LLM AUTHORITY: NONE")
print()
print("TU > ", end="", flush=True)

while True:
    try:
        user_input = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not user_input:
        print("TU > ", end="", flush=True)
        continue

    if user_input.lower() in {"exit", "quit", "esci"}:
        print("NORYX7 > Sessione terminata.")
        break

    execution_id = uuid.uuid4().hex

    bridge = ModelFabricBridge(
        fabric,
        runtime_id="noryx7-human-session",
        execution_id=execution_id,
    )

    agent = LLMBackedAgent(bridge)

    task = TaskSpec(
        task_id=uuid.uuid4().hex,
        task_type="conversation",
        objective="Rispondi all'utente in modo utile, diretto e accurato.",
        input=user_input,
        constraints={
            "tools": False,
            "external_actions": False,
            "execution_authority": False,
        },
        verification_requirements=("agent_result",),
        risk_class="normal",
        execution_id=execution_id,
    )

    result = agent.run(task)

    print()
    if result.status == "completed":
        print("NORYX7 >", result.output)
    else:
        print("NORYX7 > Errore:", result.status)

    print()
    print("TU > ", end="", flush=True)
