import pytest

from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import JournalEntry, StateJournal


def attestation(execution="exec", step="a"):
    return Attestation(execution, "user", step, "adapter", f"a-{step}", f"o-{step}", True)


def test_recovery_returns_only_committed_execution_entries():
    journal = StateJournal()
    journal.append(attestation("one", "a"))
    journal.append(attestation("two", "b"))
    journal.append(attestation("one", "c"))

    recovered = RuntimeRecovery(journal).recover("one")
    assert [entry.step_id for entry in recovered] == ["a", "c"]
    assert all(entry.execution_id == "one" for entry in recovered)


def test_recovery_rejects_duplicate_step_commits():
    journal = StateJournal()
    journal._entries.extend([
        JournalEntry(0, "exec", "a", "digest-a", "output-a"),
        JournalEntry(1, "exec", "a", "digest-a2", "output-a2"),
    ])
    with pytest.raises(RecoveryError, match="duplicate committed step"):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_non_monotonic_sequence():
    journal = StateJournal()
    journal._entries.extend([
        JournalEntry(4, "exec", "a", "digest-a", "output-a"),
        JournalEntry(3, "exec", "b", "digest-b", "output-b"),
    ])
    with pytest.raises(RecoveryError, match="strictly increasing"):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_invalid_execution_id():
    with pytest.raises(ValueError, match="invalid execution identity"):
        RuntimeRecovery(StateJournal()).recover("")
