from __future__ import annotations

import argparse
import os
import tempfile
import uuid

from core.contracts import TaskSpec
from core.frontier_capabilities import ExternalProviderCapability
from core.operational_runtime import OperationalNORYXRuntime
from noryx7_runtime.model_adapters.openrouter import OpenRouterAdapter
from noryx7_runtime.model_fabric import ModelFabric


class _SelfTestModel:
    name = "noryx7-self-test-model"
    capabilities = frozenset({"text"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        if "Begin the response with exactly APPROVE or REJECT" in prompt:
            return "APPROVE: secondary review completed without external execution."
        if "Reconcile the Primary proposal with the Secondary critique" in prompt:
            return "RECONCILED: primary and secondary outputs verified."
        return "PRIMARY PROPOSAL: bounded operational response verified."


def build_live_runtime() -> OperationalNORYXRuntime:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key.startswith("sk-or-v1-"):
        raise RuntimeError("OPENROUTER_API_KEY non configurata")
    adapter = OpenRouterAdapter(model="openrouter/free", api_key=key, timeout_seconds=120.0)
    fabric = ModelFabric([adapter], runtime_id=f"noryx7-operational-{uuid.uuid4().hex}")
    journal_path = os.environ.get("NORYX7_STATE_JOURNAL_PATH") or None
    return OperationalNORYXRuntime(model_fabric=fabric, state_journal_path=journal_path)


def _task(text: str, execution_id: str | None = None) -> TaskSpec:
    return TaskSpec(
        task_id=uuid.uuid4().hex,
        task_type="conversation",
        objective="Produce a bounded answer and use Primary-Secondary-Primary collaboration.",
        input=text,
        constraints={},
        verification_requirements=("agent_result",),
        risk_class="normal",
        execution_id=execution_id or uuid.uuid4().hex,
    )


def run_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="noryx7-selftest-") as tmp:
        journal = os.path.join(tmp, "state.sqlite3")
        fabric = ModelFabric([_SelfTestModel()], runtime_id="noryx7-self-test")
        runtime = OperationalNORYXRuntime(model_fabric=fabric, state_journal_path=journal)
        try:
            ids = set(runtime.agent_fabric.available())
            online = set(runtime.agent_fabric.online())
            required = {"noryx7-llm", "noryx7-secondary"}
            if not required.issubset(ids) or not required.issubset(online):
                raise AssertionError("primary_secondary_not_online")

            result = runtime.run_hypersynth(_task("end-to-end internal wiring test"))
            if result.get("status") != "completed":
                raise AssertionError(f"hypersynth_not_completed:{result.get('reason')}")
            if result["results"][-1].output != "RECONCILED: primary and secondary outputs verified.":
                raise AssertionError("collaboration_output_not_reconciled")

            events = runtime.audit.snapshot()
            names = {event.get("event") for event in events}
            required_events = {
                "agent_runtime_online",
                "agent_selection",
                "agent_collaboration_completed",
                "operational_fabric_dispatch_selected",
                "operational_fabric_result_admitted",
            }
            missing = required_events - names
            if missing:
                raise AssertionError(f"audit_events_missing:{sorted(missing)}")

            commit = runtime.state_journal.get(result["execution_id"])
            if commit is None:
                raise AssertionError("state_journal_commit_missing")
            recovered = runtime.state_journal.recover()
            if result["execution_id"] not in recovered:
                raise AssertionError("state_journal_recovery_missing")

            chess = runtime.capability_registry.resolve("chess_analyze")
            if chess is None:
                raise AssertionError("chess_capability_not_registered")
            chess_result = chess("start", {"depth": 1})
            if chess_result.get("status") != "completed" or not chess_result.get("legal_moves"):
                raise AssertionError("chess_capability_not_executing")

            unconfigured_provider = ExternalProviderCapability("payments", "NORYX7_PAYMENTS")
            try:
                unconfigured_provider(
                    "self-test",
                    {"operation": "self-test", "execution_id": result["execution_id"]},
                )
            except Exception as exc:
                if type(exc).__name__ != "CapabilityUnavailable":
                    raise AssertionError(f"provider_fail_closed_wrong_error:{type(exc).__name__}")
            else:
                raise AssertionError("unconfigured_provider_did_not_fail_closed")

            runtime.heartbeat_agents()
            print("NORYX7 SELF-TEST: PASS")
            print("Primary: ONLINE")
            print("Secondary: ONLINE")
            print("Operational fabric: CONNECTED")
            print("HYPERSYNTH: EXECUTED")
            print("Primary -> Secondary -> Primary: VERIFIED")
            print("State journal: PERSIST + RECOVER PASS")
            print("Chess capability: EXECUTED")
            print("High-risk provider without credentials: FAIL-CLOSED")
            return 0
        finally:
            runtime.shutdown_agents()
            if runtime.state_journal is not None:
                runtime.state_journal.close()


def run_live_once(text: str) -> int:
    runtime = build_live_runtime()
    try:
        runtime.heartbeat_agents()
        result = runtime.run_hypersynth(_task(text))
        if result.get("status") != "completed":
            verification = result.get("verification")
            reason = getattr(verification, "reason", result.get("reason", "unknown"))
            print(f"NORYX7 LIVE: REJECTED ({reason})")
            return 2
        print("NORYX7 LIVE: COMPLETED")
        print("execution_id:", result["execution_id"])
        print("agents:", [s.agent_id + ":" + s.state for s in runtime.agent_runtime.status()])
        print("response:", result["results"][-1].output)
        runtime.heartbeat_agents()
        return 0
    finally:
        runtime.shutdown_agents()


def main() -> int:
    parser = argparse.ArgumentParser(description="NORYX7 unified operational bootstrap")
    parser.add_argument("--self-test", action="store_true", help="run deterministic end-to-end wiring test")
    parser.add_argument("--once", metavar="TEXT", help="run one real OpenRouter-backed task")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.once:
        return run_live_once(args.once)
    print("Usage: python noryx7_bootstrap.py --self-test")
    print("   or: python noryx7_bootstrap.py --once 'testo'  # requires OPENROUTER_API_KEY")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
