import pytest

from noryx7_runtime.durable_state import DurableStateJournal
from noryx7_runtime.engine import RuntimeEngine
from noryx7_runtime.state import StateJournal


def test_strict_durable_state_mode_rejects_missing_journal():
    with pytest.raises(ValueError, match="durable_runtime_state_journal_required"):
        RuntimeEngine(require_durable_state_journal=True)


def test_strict_durable_state_mode_rejects_memory_only_journal():
    memory_journal = StateJournal(require_signatures=False)
    with pytest.raises(ValueError, match="durable_runtime_state_journal_required"):
        RuntimeEngine(
            runtime_id="runtime-1",
            state_journal=memory_journal,
            require_durable_state_journal=True,
        )


def test_strict_durable_state_mode_accepts_persistent_journal(tmp_path):
    journal = DurableStateJournal(
        str(tmp_path / "runtime.sqlite"),
        integrity_key=b"runtime-journal-test-key-material-32-bytes-minimum",
        key_id="test-key-v1",
        runtime_id="runtime-1",
        require_signatures=False,
    )
    engine = RuntimeEngine(
        runtime_id="runtime-1",
        state_journal=journal,
        require_durable_state_journal=True,
    )
    assert engine.runtime_id == "runtime-1"
    journal.close()


def test_strict_durable_state_mode_requires_boolean():
    with pytest.raises(TypeError, match="require_durable_state_journal"):
        RuntimeEngine(require_durable_state_journal="yes")
