from core.provider_router import Provider
from jarvis.core.contracts import Plan, PlanStep
from jarvis.core.runtime import JarvisRuntime
from jarvis.runtime_facade import JarvisFacade
from jarvis.agent.front_end import JarvisInteractionFrontEnd
from jarvis.interaction.session import SessionController
from jarvis.perception.audio import ClapDetector


def _wake():
    detector = ClapDetector()
    frontend = JarvisInteractionFrontEnd(SessionController())
    assert detector.register_clap(100, 0.95) is None
    event = detector.register_clap(300, 0.95)
    frontend.on_wake(event, session_id="provider-e2e")
    return frontend


def _plan(request_id: str) -> Plan:
    return Plan(
        request_id=request_id,
        steps=(
            PlanStep(
                step_id="provider-step",
                capability="provider_execute",
                target="provider:chat",
                parameters={
                    "provider_capability": "chat",
                    "payload": {"message": "NORYX7-PROVIDER-E2E"},
                },
            ),
        ),
    )


def test_jarvis_provider_router_to_execution_fabric_to_provider_and_state():
    calls = []

    def external_provider(parameters):
        calls.append(parameters)
        return {"provider_reply": parameters["payload"]["message"]}

    runtime = JarvisRuntime()
    runtime.register_provider(
        Provider(
            name="deterministic-provider",
            capabilities=frozenset({"chat"}),
            handler=external_provider,
        )
    )
    runtime.grant("user", "provider_execute", "provider:chat")

    request_id = "provider-runtime-001"
    frontend = _wake()
    item = frontend.build_input("usa il provider")
    result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
        item,
        _plan(request_id),
    )

    assert result.accepted is True
    assert result.reason == "executed"
    assert result.results[0].success is True
    assert result.results[0].output == {
        "provider": "deterministic-provider",
        "capability": "chat",
        "output": {"provider_reply": "NORYX7-PROVIDER-E2E"},
    }
    assert calls == [{"payload": {"message": "NORYX7-PROVIDER-E2E"}}]

    trace = runtime.execution_traces[request_id]
    assert trace.verify() is True
    committed = runtime.state.get(request_id, principal_id="user")
    assert committed is not None
    assert committed.state.status == "committed"


def test_jarvis_provider_path_fails_closed_when_provider_is_unavailable():
    calls = []

    runtime = JarvisRuntime()
    runtime.grant("user", "provider_execute", "provider:chat")

    request_id = "provider-runtime-unavailable-001"
    frontend = _wake()
    item = frontend.build_input("usa il provider")
    result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
        item,
        _plan(request_id),
    )

    assert result.accepted is False
    assert result.reason == "execution_rejected"
    assert calls == []
    assert runtime.state.get(request_id, principal_id="user") is None
    trace = runtime.execution_traces[request_id]
    assert trace.verify() is True
    assert trace.events()[-1].event_type == "execution_bridge_completed"


def test_jarvis_provider_path_fails_closed_without_user_grant():
    calls = []

    runtime = JarvisRuntime()
    runtime.register_provider(
        Provider(
            name="deterministic-provider",
            capabilities=frozenset({"chat"}),
            handler=lambda parameters: calls.append(parameters),
        )
    )

    request_id = "provider-runtime-denied-001"
    frontend = _wake()
    item = frontend.build_input("usa il provider")
    result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
        item,
        _plan(request_id),
    )

    assert result.accepted is False
    assert result.reason == "PermissionError"
    assert calls == []
    assert runtime.state.get(request_id, principal_id="user") is None
    trace = runtime.execution_traces[request_id]
    assert trace.verify() is True
    assert trace.events()[-1].event_type == "execution_denied"
