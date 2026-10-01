from jarvis.agent.front_end import AgentInput, JarvisInteractionFrontEnd
from jarvis.core.contracts import Plan, PlanStep
from jarvis.core.runtime import JarvisRuntime
from jarvis.interaction.session import SessionController
from jarvis.perception.audio import ClapDetector


def _wake_frontend():
    detector = ClapDetector()
    frontend = JarvisInteractionFrontEnd(SessionController())
    assert detector.register_clap(100, 0.95) is None
    event = detector.register_clap(300, 0.95)
    frontend.on_wake(event, session_id="e2e-session")
    return frontend


def _plan(request_id: str) -> Plan:
    return Plan(
        request_id=request_id,
        steps=(
            PlanStep(
                step_id="step-1",
                capability="echo",
                target="local:test",
                parameters={"message": "NORYX7-E2E"},
            ),
        ),
    )


def test_jarvis_frontend_to_canonical_execution_is_real_end_to_end():
    runtime = JarvisRuntime()
    runtime.registry.register(
        "echo",
        lambda target, parameters: {
            "target": target,
            "message": parameters["message"],
        },
    )
    runtime.grant("user", "echo", "local:test")

    request_id = "e2e-runtime-001"
    plan = _plan(request_id)
    frontend = _wake_frontend()
    item = frontend.build_input("esegui echo")
    assert isinstance(item, AgentInput)

    from jarvis.runtime_facade import JarvisFacade

    result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
        item, plan
    )

    assert result.accepted is True
    assert result.reason == "executed"
    assert result.results[0].success is True
    assert result.results[0].output == {
        "target": "local:test",
        "message": "NORYX7-E2E",
    }

    trace = runtime.execution_traces[request_id]
    assert trace.verify() is True
    assert [event.event_type for event in trace.events()] == [
        "execution_requested",
        "execution_started",
        "execution_bridge_completed",
        "state_committed",
        "execution_finished",
    ]

    committed = runtime.state.get(request_id, principal_id="user")
    assert committed is not None
    assert committed.state.status == "committed"


def test_jarvis_end_to_end_fails_closed_without_user_grant():
    runtime = JarvisRuntime()
    runtime.registry.register("echo", lambda target, parameters: parameters["message"])

    request_id = "e2e-runtime-denied-001"
    plan = _plan(request_id)
    frontend = _wake_frontend()
    item = frontend.build_input("esegui echo")

    from jarvis.runtime_facade import JarvisFacade

    result = JarvisFacade(runtime=runtime, frontend=frontend).accept_input(
        item, plan
    )

    assert result.accepted is False
    assert result.reason == "PermissionError"
    assert request_id in runtime.execution_traces
    trace = runtime.execution_traces[request_id]
    assert trace.verify() is True
    assert trace.events()[-1].event_type == "execution_denied"
    assert runtime.state.get(request_id, principal_id="user") is None
