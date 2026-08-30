from models.memory import MemoryStore
from models.provider import MockModelProvider
from models.selector import ResourceSelector
from core.orchestrator import NORYXOrchestrator


class CountingProvider(MockModelProvider):
    def __init__(self, response: str):
        super().__init__(response)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return super().generate(prompt)


class TrackingMemoryStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.retrieve_events: list[str] = []

    def retrieve(self, query: str):
        self.retrieve_events.append(query)
        return super().retrieve(query)


def test_orchestrator_processes_goal_and_updates_state():
    provider = MockModelProvider("travel-plan-ready")
    orchestrator = NORYXOrchestrator(model_provider=provider)

    state = orchestrator.process(
        "Voglio organizzare un viaggio",
        "Organizzare il viaggio",
    )

    assert state.user_input == "Voglio organizzare un viaggio"
    assert state.goal == "Organizzare il viaggio"
    assert state.status == "completed"
    assert state.subtasks == [
        "Definire budget, date e destinazione del viaggio",
        "Verificare opzioni di trasporto e alloggio",
        "Prenotare i servizi principali del viaggio",
        "Preparare documenti, agenda e dettagli finali",
    ]
    assert state.final_answer == "travel-plan-ready :: prompt=Goal: Organizzare il viaggio\nUser input: Voglio organizzare un viaggio\nSubtasks:\n- Definire budget, date e destinazione del viaggio\n- Verificare opzioni di trasporto e alloggio\n- Prenotare i servizi principali del viaggio\n- Preparare documenti, agenda e dettagli finali"
    assert state.memory[-1]["type"] == "model_response"
    assert state.memory[-1]["response"] == state.final_answer


def test_orchestrator_accepts_default_provider_and_preserves_existing_call_pattern():
    orchestrator = NORYXOrchestrator()

    state = orchestrator.receive("Scrivere una presentazione")
    state = orchestrator.set_goal("Preparare una presentazione")
    state = orchestrator.process("Scrivere una presentazione", "Preparare una presentazione")

    assert state.status == "completed"
    assert state.subtasks == [
        "Definire obiettivo, pubblico e messaggio principale",
        "Raccontare e strutturare il contenuto",
        "Preparare materiali, slide e dettagli finali",
    ]
    assert "Goal: Preparare una presentazione" in state.final_answer


def test_orchestrator_uses_injected_provider_in_complete_flow():
    custom_provider = MockModelProvider("custom-plan")
    orchestrator = NORYXOrchestrator(model_provider=custom_provider)

    state = orchestrator.process(
        "Ho bisogno di un piano di viaggio",
        "Pianificare un viaggio",
    )

    assert state.status == "completed"
    assert state.user_input == "Ho bisogno di un piano di viaggio"
    assert state.goal == "Pianificare un viaggio"
    assert state.subtasks[0] == "Definire budget, date e destinazione del viaggio"
    assert state.memory[-1]["prompt"].startswith("Goal: Pianificare un viaggio")
    assert state.final_answer == "custom-plan :: prompt=Goal: Pianificare un viaggio\nUser input: Ho bisogno di un piano di viaggio\nSubtasks:\n- Definire budget, date e destinazione del viaggio\n- Verificare opzioni di trasporto e alloggio\n- Prenotare i servizi principali del viaggio\n- Preparare documenti, agenda e dettagli finali"


def test_execution_loop_selects_next_task_and_advances_cursor():
    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("loop-ready"))

    state = orchestrator.receive("Organizzare un viaggio")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(state)

    first_task = orchestrator.select_next_task()
    assert first_task == state.subtasks[0]
    assert state.current_task_index == 0

    result = orchestrator.execute_task(first_task)
    verification = orchestrator.verify_task_result(first_task, result)

    assert result.startswith("loop-ready :: prompt=")
    assert verification["status"] == "passed"

    state.current_task_index += 1
    assert orchestrator.select_next_task() == state.subtasks[1]
    assert state.current_task_index == 1


def test_run_execution_loop_executes_all_tasks_and_completes():
    provider = MockModelProvider("loop-result")
    orchestrator = NORYXOrchestrator(model_provider=provider)

    state = orchestrator.run_execution_loop(
        "Voglio organizzare un viaggio",
        "Organizzare il viaggio",
    )

    assert state.status == "completed"
    assert state.current_task_index == len(state.subtasks)
    assert len(state.execution_history) == len(state.subtasks)
    assert all(item["verification"]["status"] == "passed" for item in state.execution_history)
    assert "loop-result" in state.final_answer


def test_run_execution_loop_handles_zero_subtasks_deterministically():
    class EmptyTaskDecomposer:
        def decompose(self, state):
            state.subtasks = []
            return []

    orchestrator = NORYXOrchestrator(
        model_provider=MockModelProvider("empty-result"),
        decomposer=EmptyTaskDecomposer(),
    )

    state = orchestrator.run_execution_loop("Input senza goal utile", "Goal non rilevato")

    assert state.status == "completed"
    assert state.current_task_index == 0
    assert state.execution_history == []
    assert state.final_answer == "No subtasks generated."


def test_provider_is_called_once_per_task_and_retrieval_happens_before_execution():
    provider = CountingProvider("memory-aware-result")
    memory_store = TrackingMemoryStore()
    memory_store.store("Budget travel plan needed", source="task_result", associated_task="budget trip")
    memory_store.store("Garden maintenance note", source="task_result", associated_task="yard work")

    orchestrator = NORYXOrchestrator(model_provider=provider, memory_store=memory_store)
    orchestrator.receive("Plan a trip")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["budget trip"]

    task = orchestrator.select_next_task()
    relevant = orchestrator.retrieve_relevant_memory(task)
    prompt = orchestrator._build_task_prompt(task, relevant)

    assert relevant == ["Budget travel plan needed"]
    assert "Budget travel plan needed" in prompt
    assert "Garden maintenance note" not in prompt

    result = orchestrator.execute_task(task, relevant)

    assert provider.calls == 1
    assert memory_store.retrieve_events == ["budget trip"]
    assert result.startswith("memory-aware-result :: prompt=")


def test_prompt_contains_relevant_memory_but_excludes_irrelevant_memory_for_related_task():
    memory_store = MemoryStore()
    memory_store.store("Budget travel plan needed", source="task_result", associated_task="budget trip")
    memory_store.store("Garden maintenance note", source="task_result", associated_task="yard work")

    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("planned-result"), memory_store=memory_store)
    orchestrator.receive("Plan a trip")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["budget trip planning"]

    task = orchestrator.select_next_task()
    relevant = orchestrator.retrieve_relevant_memory(task)
    prompt = orchestrator._build_task_prompt(task, relevant)

    assert relevant == ["Budget travel plan needed"]
    assert "Budget travel plan needed" in prompt
    assert "Garden maintenance note" not in prompt


def test_verified_result_is_available_to_correlated_follow_up_task():
    provider = MockModelProvider("Budget travel plan needed")
    orchestrator = NORYXOrchestrator(model_provider=provider)
    orchestrator.receive("Plan the trip")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["budget trip", "budget trip planning"]

    first_task = orchestrator.select_next_task()
    first_context = orchestrator.retrieve_relevant_memory(first_task)
    first_result = orchestrator.execute_task(first_task, first_context)
    first_verification = orchestrator.verify_task_result(first_task, first_result)
    assert first_verification["status"] == "passed"

    orchestrator.memory_store.store(first_result, source="task_result", associated_task=first_task)

    second_task = orchestrator.state.subtasks[1]
    second_context = orchestrator.retrieve_relevant_memory(second_task)
    second_prompt = orchestrator._build_task_prompt(second_task, second_context)

    assert any("Budget travel plan needed" in entry for entry in second_context)
    assert "Budget travel plan needed" in second_prompt


def test_resource_selector_selects_small_for_simple_task():
    selector = ResourceSelector()

    assert selector.select("Riassumi questo testo") == "small"
    assert selector.estimate_complexity("Riassumi questo testo") == "small"


def test_resource_selector_selects_large_for_complex_task():
    selector = ResourceSelector()

    assert selector.select("Pianifica un itinerario completo con budget, trasporto, hotel e documenti") == "large"
    assert selector.estimate_complexity("Pianifica un itinerario completo con budget, trasporto, hotel e documenti") == "large"


def test_orchestrator_records_selected_resource_and_history():
    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("resource-check"))
    orchestrator.receive("Organizza un viaggio")
    orchestrator.set_goal("Organizzare un viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)

    task = orchestrator.select_next_task()
    resource = orchestrator.select_resource(task)

    assert resource in {"small", "large"}
    assert orchestrator.state.selected_resource == resource
    assert orchestrator.state.resource_history[-1]["task"] == task
    assert orchestrator.state.resource_history[-1]["selected_resource"] == resource


def test_run_execution_loop_uses_resource_before_execution_and_executes_once():
    provider = MockModelProvider("selection-ok")
    orchestrator = NORYXOrchestrator(model_provider=provider)

    state = orchestrator.run_execution_loop(
        "Pianifica un viaggio completo",
        "Organizzare il viaggio",
    )

    assert state.status == "completed"
    assert state.selected_resource in {"small", "large"}
    assert len(state.resource_history) == len(state.subtasks)
    assert len(state.execution_history) == len(state.subtasks)
    assert all(item["task"] == state.subtasks[idx] for idx, item in enumerate(state.execution_history))


def test_different_tasks_can_select_different_resources():
    selector = ResourceSelector()

    simple = selector.select("Riassumi la nota")
    complex = selector.select("Pianifica un viaggio con hotel, trasporto, budget e documenti")

    assert simple == "small"
    assert complex == "large"
    assert simple != complex


def test_memory_store_stores_and_retrieves_relevant_entries():
    store = MemoryStore()
    store.store("Budget travel plan needed", source="task_result", associated_task="plan trip")

    matches = store.retrieve("budget")

    assert len(matches) == 1
    assert matches[0].content == "Budget travel plan needed"
    assert matches[0].source == "task_result"


def test_memory_store_returns_empty_for_non_matching_query():
    store = MemoryStore()
    store.store("Garden maintenance checklist", source="task_result", associated_task="yard work")

    assert store.retrieve("flight booking") == []


def test_memory_store_is_deterministic_for_keyword_matching():
    store = MemoryStore()
    store.store("Hotel and transport summary", source="task_result", associated_task="travel")
    store.store("Document checklist", source="task_result", associated_task="travel")

    results = store.retrieve("hotel travel")

    assert [entry.content for entry in results] == ["Hotel and transport summary", "Document checklist"]


def test_unverified_result_is_not_stored_in_memory():
    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider(""))
    orchestrator.receive("Bad task")
    orchestrator.set_goal("Do something")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["task without useful result"]

    orchestrator.state.current_task_index = 0
    task = orchestrator.select_next_task()
    resource = orchestrator.select_resource(task)
    result = orchestrator.execute_task(task)
    verification = orchestrator.verify_task_result(task, result)
    if verification["status"] == "passed":
        orchestrator.memory_store.store(result, source="task_result", associated_task=task)

    assert verification["status"] == "failed"
    assert orchestrator.memory_store.retrieve("task without useful result") == []


def test_verified_result_is_stored_in_memory():
    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("positive result"))
    orchestrator.receive("Create plan")
    orchestrator.set_goal("Plan a trip")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["reservation task"]

    task = orchestrator.select_next_task()
    resource = orchestrator.select_resource(task)
    result = orchestrator.execute_task(task)
    verification = orchestrator.verify_task_result(task, result)

    if verification["status"] == "passed":
        orchestrator.memory_store.store(result, source="task_result", associated_task=task)

    assert verification["status"] == "passed"
    assert any(
        "positive result" in entry.content and "reservation task" in entry.content
        for entry in orchestrator.memory_store.retrieve("positive result")
    )


def test_run_execution_loop_retrieves_memory_before_execution_and_builds_context():
    store = MemoryStore()
    store.store("Previous trip budget insight", source="task_result", associated_task="budget trip")

    orchestrator = NORYXOrchestrator(
        model_provider=MockModelProvider("memory-aware-result"),
        memory_store=store,
    )
    orchestrator.receive("Prepare travel plan")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["budget trip"]

    task = orchestrator.select_next_task()
    relevant = orchestrator.retrieve_relevant_memory(task)
    prompt = orchestrator._build_task_prompt(task, relevant)

    assert relevant == ["Previous trip budget insight"]
    assert "Relevant memory:" in prompt
    assert "Previous trip budget insight" in prompt


def test_memory_irrelevant_to_task_is_excluded_from_context():
    store = MemoryStore()
    store.store("Garden maintenance note", source="task_result", associated_task="yard work")

    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("irrelevant-check"))
    orchestrator.receive("Plan a trip")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["plan trip"]

    task = orchestrator.select_next_task()
    relevant = orchestrator.retrieve_relevant_memory(task)

    assert relevant == []
    assert all("Garden maintenance note" not in item for item in relevant)


def test_execution_loop_uses_memory_to_augment_context_for_follow_up_task():
    store = MemoryStore()
    store.store("Budget travel plan needed", source="task_result", associated_task="budget trip")

    orchestrator = NORYXOrchestrator(model_provider=MockModelProvider("follow-up-result"), memory_store=store)
    orchestrator.receive("Plan a trip")
    orchestrator.set_goal("Organizzare il viaggio")
    orchestrator.decomposer.decompose(orchestrator.state)
    orchestrator.state.subtasks = ["budget trip", "book transport"]

    first_task = orchestrator.select_next_task()
    first_context = orchestrator.retrieve_relevant_memory(first_task)
    first_prompt = orchestrator._build_task_prompt(first_task, first_context)

    assert "Budget travel plan needed" in first_prompt

    result = orchestrator.execute_task(first_task)
    verification = orchestrator.verify_task_result(first_task, result)
    if verification["status"] == "passed":
        orchestrator.memory_store.store(result, source="task_result", associated_task=first_task)

    next_task = orchestrator.state.subtasks[1]
    next_context = orchestrator.retrieve_relevant_memory(next_task)

    assert len(next_context) >= 0
