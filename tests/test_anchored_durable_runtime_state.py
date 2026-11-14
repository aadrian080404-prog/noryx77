import shutil

import pytest

from core.journal_integrity import InMemoryMonotonicAnchor
from noryx7_runtime.anchored_durable_state import AnchoredDurableStateJournal


KEY = b"r" * 32


class ToggleAnchor:
    def __init__(self):
        self.inner = InMemoryMonotonicAnchor()
        self.fail_writes = False

    def read(self):
        return self.inner.read()

    def compare_and_swap(self, expected, replacement):
        if self.fail_writes:
            return False
        return self.inner.compare_and_swap(expected, replacement)


def make_journal(path, anchor):
    return AnchoredDurableStateJournal(
        str(path),
        anchor=anchor,
        integrity_key=KEY,
        key_id="runtime-test-key",
        require_signatures=False,
        runtime_id="runtime-test",
    )


def test_anchored_runtime_journal_advances_anchor_and_recovers_reservations(tmp_path):
    path = tmp_path / "runtime.sqlite"
    anchor = InMemoryMonotonicAnchor()
    journal = make_journal(path, anchor)
    reservation = journal.reserve_step("exec-1", "principal-1", "step-1", "a" * 64)
    assert anchor.read() == journal.snapshot_anchor()
    assert anchor.read().sequence == 1
    journal.close()

    recovered = make_journal(path, anchor)
    assert recovered.reservation("exec-1", "step-1") == reservation
    assert recovered.durable is True
    recovered.close()


def test_anchored_runtime_journal_detects_database_snapshot_rollback(tmp_path):
    path = tmp_path / "runtime.sqlite"
    backup = tmp_path / "runtime-before-second-event.sqlite"
    anchor = InMemoryMonotonicAnchor()
    journal = make_journal(path, anchor)
    journal.reserve_step("exec-1", "principal-1", "step-1", "a" * 64)
    journal.close()
    shutil.copy2(path, backup)

    journal = make_journal(path, anchor)
    journal.reserve_step("exec-2", "principal-1", "step-2", "b" * 64)
    journal.close()
    shutil.copy2(backup, path)

    with pytest.raises(RuntimeError, match="runtime_journal_anchor_mismatch"):
        make_journal(path, anchor)


def test_anchored_runtime_journal_recovers_single_commit_before_anchor_cas(tmp_path):
    path = tmp_path / "runtime.sqlite"
    anchor = ToggleAnchor()
    journal = make_journal(path, anchor)
    anchor.fail_writes = True
    with pytest.raises(RuntimeError, match="anchor_update_failed"):
        journal.reserve_step("exec-1", "principal-1", "step-1", "a" * 64)
    journal.close()

    anchor.fail_writes = False
    recovered = make_journal(path, anchor)
    assert anchor.read().sequence == 1
    assert recovered.reservation("exec-1", "step-1") is not None
    recovered.close()


def test_anchored_runtime_journal_fails_closed_when_anchor_is_behind_by_more_than_one(tmp_path):
    path = tmp_path / "runtime.sqlite"
    anchor = InMemoryMonotonicAnchor()
    journal = make_journal(path, anchor)
    journal.reserve_step("exec-1", "principal-1", "step-1", "a" * 64)
    journal.reserve_step("exec-2", "principal-1", "step-2", "b" * 64)
    journal.close()

    with pytest.raises(RuntimeError, match="runtime_journal_anchor_mismatch"):
        make_journal(path, InMemoryMonotonicAnchor())
