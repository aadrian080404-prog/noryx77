from __future__ import annotations

import os
import uuid

from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from noryx7_runtime.model_fabric import ModelFabric


def build_runtime() -> OperationalNORYXRuntime:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key.startswith("sk-or-v1-"):
        raise RuntimeError("OPENROUTER_API_KEY non configurata")
    adapter = OpenRouterAdapter(model="openrouter/free", api_key=key, timeout_seconds=120.0)
    fabric = ModelFabric([adapter], runtime_id=f"noryx7-operational-{uuid.uuid4().hex}")
    return OperationalNORYXRuntime(model_fabric=fabric)


def main() -> None:
    runtime = build_runtime()
    print("NORYX7 OPERATIONAL RUNTIME: ONLINE")
    for status in runtime.agent_runtime.status():
        print(f"{status.agent_id}: {status.state} ({status.role})")
    print("Primary -> Secondary -> Primary: ENABLED")
    print("Type 'esci' to stop.")
    try:
        while True:
            user_input = input("TU > ").strip()
            if user_input.lower() in {"esci", "exit", "quit"}:
                break
            if not user_input:
                continue
            task = TaskSpec(
                task_id=uuid.uuid4().hex,
                task_type="conversation",
                objective="Rispondi all'utente in modo utile, accurato e verificato; usa la collaborazione Primary-Secondary-Primary.",
                input=user_input,
                constraints={},
                verification_requirements=("agent_result",),
                risk_class="normal",
                execution_id=uuid.uuid4().hex,
            )
            result = runtime.run_hypersynth(task)
            if result.get("status") == "completed":
                print("NORYX7 >", result["results"][-1].output)
            else:
                verification = result.get("verification")
                print("NORYX7 > execution rejected:", getattr(verification, "reason", result.get("reason", "unknown")))
            runtime.heartbeat_agents()
    finally:
        runtime.shutdown_agents()
        print("NORYX7 OPERATIONAL RUNTIME: OFFLINE")


if __name__ == "__main__":
    main()
