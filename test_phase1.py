from core.core.orchestrator import NORYXOrchestrator
from core.state import NORYXState


def test_noryx_state_defaults():
    state = NORYXState()

    assert state.user_input == ""
    assert state.context == []
    assert state.goal == ""
    assert state.subtasks == []
    assert state.memory == []
    assert state.available_tools == []
    assert state.selected_models == []
    assert state.hypotheses == []
    assert state.verification_results == []
    assert state.confidence == 0.0
    assert state.current_action == ""
    assert state.final_answer == ""
    assert state.status == "initialized"


def test_orchestrator_initialization():
    orchestrator = NORYXOrchestrator()

    assert isinstance(orchestrator.state, NORYXState)
    assert orchestrator.state is not None


def test_receive_updates_input_and_status():
    orchestrator = NORYXOrchestrator()
    state = orchestrator.receive("hello world")

    assert state.user_input == "hello world"
    assert state.status == "processing"


def test_set_goal_updates_goal_only():
    orchestrator = NORYXOrchestrator()
    orchestrator.receive("hello")

    orchestrator.set_goal("solve task")
    state = orchestrator.state

    assert state.goal == "solve task"
    assert state.user_input == "hello"
    assert state.status == "processing"


def test_complete_sets_answer_and_completed_status():
    orchestrator = NORYXOrchestrator()
    orchestrator.receive("hello")
    orchestrator.set_goal("solve task")

    state = orchestrator.complete("done")

    assert state.final_answer == "done"
    assert state.status == "completed"
    assert state.goal == "solve task"


def test_lifecycle_progresses_initialized_to_processing_to_completed():
    orchestrator = NORYXOrchestrator()
    assert orchestrator.state.status == "initialized"

    orchestrator.receive("prompt")
    assert orchestrator.state.status == "processing"

    orchestrator.complete("result")
    assert orchestrator.state.status == "completed"


def test_single_state_instance_is_preserved():
    orchestrator = NORYXOrchestrator()
    first = orchestrator.state

    orchestrator.receive("a")
    orchestrator.set_goal("b")
    orchestrator.complete("c")

    assert orchestrator.state is first
    assert orchestrator.state.user_input == "a"
    assert orchestrator.state.goal == "b"
    assert orchestrator.state.final_answer == "c"


def test_no_undeclared_mutations_on_known_fields():
    orchestrator = NORYXOrchestrator()
    state = orchestrator.state

    orchestrator.receive("prompt")
    orchestrator.set_goal("goal")
    orchestrator.complete("answer")

    assert set(state.__dict__.keys()) == {
        "user_input",
        "context",
        "goal",
        "subtasks",
        "memory",
        "available_tools",
        "selected_models",
        "hypotheses",
        "verification_results",
        "confidence",
        "current_action",
        "final_answer",
        "status",
    }
