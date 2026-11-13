"""SQLite state journal coordinated with an external monotonic anchor."""
from __future__ import annotations

from .journal_integrity import AnchorSnapshot, MonotonicAnchor, ZERO_MAC
from .state import StateCommit
from .state_journal import StateJournal


class AnchoredStateJournal(StateJournal):
    """Detects database rollback using a witness outside the SQLite rollback domain.

    A single committed DB record ahead of the witness is treated as the known
    crash window (DB commit completed, witness CAS did not) and may be advanced
    after the full local chain is reverified. Any larger/mismatched divergence
    fails closed.
    """

    def __init__(self, path: str, *, anchor: MonotonicAnchor, integrity_key: bytes,
                 key_id: str, max_commits: int = 10_000) -> None:
        if not callable(getattr(anchor, "read", None)) or not callable(
            getattr(anchor, "compare_and_swap", None)
        ):
            raise TypeError("monotonic_anchor_contract_required")
        self._anchor = anchor
        super().__init__(path, integrity_key=integrity_key, key_id=key_id, max_commits=max_commits)
        try:
            with self._lock:
                self._reconcile_anchor_locked()
        except Exception:
            self._db.close()
            raise

    def _local_head_locked(self) -> AnchorSnapshot:
        self._recover_locked()
        row = self._db.execute(
            "SELECT sequence,record_mac FROM state_commits ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        return AnchorSnapshot(0, ZERO_MAC) if row is None else AnchorSnapshot(int(row[0]), row[1])

    def _reconcile_anchor_locked(self) -> AnchorSnapshot:
        local = self._local_head_locked()
        remote = self._anchor.read()
        if not isinstance(remote, AnchorSnapshot):
            raise RuntimeError("state_journal_anchor_snapshot_invalid")
        if remote == local:
            return local
        if local.sequence == remote.sequence + 1:
            row = self._db.execute(
                "SELECT previous_mac FROM state_commits WHERE sequence=?",
                (local.sequence,),
            ).fetchone()
            if row is not None and row[0] == remote.mac:
                if self._anchor.compare_and_swap(remote, local):
                    return local
                if self._anchor.read() == local:
                    return local
        raise RuntimeError("state_journal_anchor_mismatch")

    def append(self, commit: StateCommit) -> None:
        if not isinstance(commit, StateCommit):
            raise TypeError("state_commit_required")
        with self._lock:
            self._reconcile_anchor_locked()
            existing = self._recover_locked().get(commit.execution_id)
            if existing is not None:
                if existing == commit:
                    return
                raise PermissionError("execution_already_journaled")
            previous = self._local_head_locked()
            super().append(commit)
            current = self._local_head_locked()
            if current.sequence != previous.sequence + 1:
                raise RuntimeError("state_journal_anchor_sequence_invalid")
            if not self._anchor.compare_and_swap(previous, current):
                if self._anchor.read() != current:
                    raise RuntimeError("state_journal_anchor_update_failed")

    def get(self, execution_id: str) -> StateCommit | None:
        with self._lock:
            self._reconcile_anchor_locked()
            return super().get(execution_id)

    def recover(self):
        with self._lock:
            self._reconcile_anchor_locked()
            return super().recover()
