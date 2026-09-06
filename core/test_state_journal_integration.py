import hashlib

from .state import NORYXState, StateStore
from .state_journal import StateJournal


def test_state_store_rehydrates_from_durable_journal(tmp_path):
    path = str(tmp_path / "state.db")
    digest = hashlib.sha256(b"input").hexdigest()
    state = NORYXState(input_digest=digest, goal="goal", confidence=1.0)

    journal = StateJournal(path)
    store = StateStore(journal=journal)
    committed = store.commit(
        state,
        execution_id="exec-1",
        task_id="task-1",
        verification_valid=True,
        verification_stage="runtime_result",
        principal_id="deterministic",
        principal_key_fingerprint="a" * 64,
    )
    journal.close()

    reopened_journal = StateJournal(path)
    reopened = StateStore(journal=reopened_journal)
    recovered = reopened.get("exec-1")
    assert recovered is not None
    assert recovered.sequence == committed.sequence == 1
    assert recovered.state.goal == "goal"
    reopened_journal.close()
