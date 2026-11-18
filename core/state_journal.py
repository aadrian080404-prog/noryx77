"""Durable, crash-recoverable journal for verified NORYX7 state commits.

The journal stores only canonical JSON state snapshots and identity metadata.
SQLite provides transactional durability; the application remains responsible
for choosing a storage location with the required OS/filesystem protections.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import sqlite3
from threading import RLock
from typing import Any

from .state import NORYXState, StateCommit
from .journal_integrity import AnchorSnapshot, JournalAuthenticator, JournalRecordProof, ZERO_MAC


class StateJournal:
    """Append-only durable commit journal with replay and tamper checks."""

    SCHEMA_VERSION = 1

    def __init__(
        self, path: str, *, max_commits: int = 10_000,
        authenticator: JournalAuthenticator | None = None,
    ) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("journal_path_required")
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits_must_be_positive")
        if authenticator is not None and not isinstance(authenticator, JournalAuthenticator):
            raise TypeError("journal_authenticator_required")
        self.authenticator = authenticator
        self.path = path
        self.max_commits = max_commits
        self._lock = RLock()
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS state_journal_proofs ("
            "sequence INTEGER PRIMARY KEY, previous_mac TEXT NOT NULL, "
            "payload_digest TEXT NOT NULL, key_id TEXT NOT NULL, mac TEXT NOT NULL)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS state_commits ("
            "execution_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, state_json TEXT NOT NULL, "
            "verification_stage TEXT NOT NULL, sequence INTEGER NOT NULL UNIQUE, "
            "principal_id TEXT NOT NULL, principal_key_fingerprint TEXT NOT NULL, "
            "record_digest TEXT NOT NULL, schema_version INTEGER NOT NULL)"
        )

    @staticmethod
    def _canonical(commit: StateCommit) -> str:
        payload: dict[str, Any] = {
            "execution_id": commit.execution_id,
            "task_id": commit.task_id,
            "state": asdict(commit.state),
            "verification_stage": commit.verification_stage,
            "sequence": commit.sequence,
            "principal_id": commit.principal_id,
            "principal_key_fingerprint": commit.principal_key_fingerprint,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _digest(cls, commit: StateCommit) -> str:
        return hashlib.sha256(cls._canonical(commit).encode("utf-8")).hexdigest()

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> StateCommit:
        execution_id, task_id, state_json, verification_stage, sequence, principal_id, fingerprint, digest, schema = row
        if schema != StateJournal.SCHEMA_VERSION:
            raise RuntimeError("unsupported_journal_schema")
        raw = json.loads(state_json)
        state = NORYXState(**raw)
        commit = StateCommit(execution_id, task_id, state, verification_stage, sequence, principal_id, fingerprint)
        if StateJournal._digest(commit) != digest:
            raise RuntimeError("state_journal_integrity_failure")
        return commit

    @staticmethod
    def _proof_from_row(row: tuple[Any, ...]) -> JournalRecordProof:
        return JournalRecordProof(
            sequence=row[0], previous_mac=row[1], payload_digest=row[2],
            key_id=row[3], mac=row[4],
        )

    def _initialize_proof_chain(self) -> None:
        """Backfill authenticated proofs for a legacy journal after digest checks."""
        with self._lock:
            rows = self._db.execute(
                "SELECT execution_id,task_id,state_json,verification_stage,sequence,"
                "principal_id,principal_key_fingerprint,record_digest,schema_version "
                "FROM state_commits ORDER BY sequence"
            ).fetchall()
            proof_count = self._db.execute(
                "SELECT COUNT(*) FROM state_journal_proofs"
            ).fetchone()[0]
            if proof_count not in (0, len(rows)):
                raise RuntimeError("state_journal_proof_chain_incomplete")
            if proof_count == len(rows):
                self._verify_proof_chain_locked()
                return
            commits = [self._from_row(row) for row in rows]
            previous = ZERO_MAC
            self._db.execute("BEGIN IMMEDIATE")
            try:
                for commit in commits:
                    proof = self.authenticator.create(
                        commit.sequence, previous, self._canonical(commit).encode("utf-8")
                    )
                    self._db.execute(
                        "INSERT INTO state_journal_proofs VALUES (?, ?, ?, ?, ?)",
                        (proof.sequence, proof.previous_mac, proof.payload_digest,
                         proof.key_id, proof.mac),
                    )
                    previous = proof.mac
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def _verify_proof_chain_locked(self) -> AnchorSnapshot:
        if self.authenticator is None:
            raise RuntimeError("state_journal_authenticator_required")
        rows = self._db.execute(
            "SELECT c.execution_id,c.task_id,c.state_json,c.verification_stage,c.sequence,"
            "c.principal_id,c.principal_key_fingerprint,c.record_digest,c.schema_version,"
            "p.sequence,p.previous_mac,p.payload_digest,p.key_id,p.mac "
            "FROM state_commits c LEFT JOIN state_journal_proofs p ON p.sequence=c.sequence "
            "ORDER BY c.sequence"
        ).fetchall()
        proof_count = self._db.execute(
            "SELECT COUNT(*) FROM state_journal_proofs"
        ).fetchone()[0]
        if proof_count != len(rows):
            raise RuntimeError("state_journal_proof_chain_orphaned")
        expected = 1
        previous = ZERO_MAC
        for row in rows:
            commit = self._from_row(row[:9])
            if row[9] is None:
                raise RuntimeError("state_journal_proof_missing")
            proof = self._proof_from_row(row[9:14])
            if (
                proof.sequence != expected
                or proof.previous_mac != previous
                or not self.authenticator.verify(
                    proof, self._canonical(commit).encode("utf-8")
                )
            ):
                raise RuntimeError("state_journal_authentication_failure")
            expected += 1
            previous = proof.mac
        return AnchorSnapshot(expected - 1, previous)

    def verify_and_advance_anchor(self, anchor) -> AnchorSnapshot:
        """Verify the HMAC chain and monotonically publish its head outside SQLite."""
        if not callable(getattr(anchor, "read", None)) or not callable(
            getattr(anchor, "compare_and_swap", None)
        ):
            raise TypeError("state_journal_monotonic_anchor_required")
        with self._lock:
            head = self._verify_proof_chain_locked()
            anchored = anchor.read()
            if not isinstance(anchored, AnchorSnapshot):
                raise RuntimeError("state_journal_anchor_snapshot_invalid")
            if (
                isinstance(anchored.sequence, bool)
                or not isinstance(anchored.sequence, int)
                or anchored.sequence < 0
                or not isinstance(anchored.mac, str)
            ):
                raise RuntimeError("state_journal_anchor_snapshot_invalid")
            if anchored.sequence > head.sequence:
                raise RuntimeError("state_journal_rollback_detected")
            proofs = self._db.execute(
                "SELECT mac FROM state_journal_proofs ORDER BY sequence"
            ).fetchall()
            expected_mac = ZERO_MAC if anchored.sequence == 0 else proofs[anchored.sequence - 1][0]
            if anchored.mac != expected_mac:
                raise RuntimeError("state_journal_anchor_mismatch")
            current = anchored
            for sequence in range(anchored.sequence + 1, head.sequence + 1):
                replacement = AnchorSnapshot(sequence, proofs[sequence - 1][0])
                try:
                    accepted = anchor.compare_and_swap(current, replacement)
                except Exception as exc:
                    try:
                        latest = anchor.read()
                    except Exception as read_exc:
                        raise RuntimeError("state_journal_anchor_outcome_uncertain") from read_exc
                    if latest == replacement:
                        current = replacement
                        continue
                    raise RuntimeError("state_journal_anchor_outcome_uncertain") from exc
                if accepted:
                    current = replacement
                    continue
                try:
                    latest = anchor.read()
                except Exception as exc:
                    raise RuntimeError("state_journal_anchor_outcome_uncertain") from exc
                if latest == replacement:
                    current = replacement
                    continue
                raise RuntimeError("state_journal_anchor_compare_and_swap_failed")
            return head

    def append(self, commit: StateCommit) -> None:
        with self._lock:
            if self._db.execute("SELECT 1 FROM state_commits WHERE execution_id=?", (commit.execution_id,)).fetchone():
                raise PermissionError("execution_already_journaled")
            count = self._db.execute("SELECT COUNT(*) FROM state_commits").fetchone()[0]
            if count >= self.max_commits:
                raise MemoryError("journal_capacity_exceeded")
            digest = self._digest(commit)
            state_json = json.dumps(asdict(commit.state), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            try:
                self._db.execute("BEGIN IMMEDIATE")
                if self.authenticator is None:
                    proof_count = self._db.execute(
                        "SELECT COUNT(*) FROM state_journal_proofs"
                    ).fetchone()[0]
                    if proof_count:
                        raise RuntimeError("state_journal_authenticator_required")
                proof = None
                if self.authenticator is not None:
                    previous_row = self._db.execute(
                        "SELECT mac FROM state_journal_proofs ORDER BY sequence DESC LIMIT 1"
                    ).fetchone()
                    previous_mac = previous_row[0] if previous_row else ZERO_MAC
                    proof = self.authenticator.create(
                        commit.sequence, previous_mac, self._canonical(commit).encode("utf-8")
                    )
                self._db.execute(
                    "INSERT INTO state_commits VALUES (?,?,?,?,?,?,?,?,?)",
                    (commit.execution_id, commit.task_id, state_json, commit.verification_stage,
                     commit.sequence, commit.principal_id, commit.principal_key_fingerprint,
                     digest, self.SCHEMA_VERSION),
                )
                if proof is not None:
                    self._db.execute(
                        "INSERT INTO state_journal_proofs VALUES (?, ?, ?, ?, ?)",
                        (proof.sequence, proof.previous_mac, proof.payload_digest,
                         proof.key_id, proof.mac),
                    )
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def get(self, execution_id: str) -> StateCommit | None:
        with self._lock:
            row = self._db.execute(
                "SELECT execution_id,task_id,state_json,verification_stage,sequence,principal_id,principal_key_fingerprint,record_digest,schema_version "
                "FROM state_commits WHERE execution_id=?", (execution_id,)
            ).fetchone()
            return None if row is None else self._from_row(row)

    def recover(self) -> dict[str, StateCommit]:
        with self._lock:
            proof_count = self._db.execute(
                "SELECT COUNT(*) FROM state_journal_proofs"
            ).fetchone()[0]
            if proof_count and self.authenticator is None:
                raise RuntimeError("state_journal_authenticator_required")
            if self.authenticator is not None:
                self._verify_proof_chain_locked()
            rows = self._db.execute(
                "SELECT execution_id,task_id,state_json,verification_stage,sequence,principal_id,principal_key_fingerprint,record_digest,schema_version "
                "FROM state_commits ORDER BY sequence"
            ).fetchall()
            commits = [self._from_row(row) for row in rows]
            expected = 1
            for commit in commits:
                if commit.sequence != expected:
                    raise RuntimeError("state_journal_sequence_gap")
                expected += 1
            return {commit.execution_id: commit for commit in commits}

    def close(self) -> None:
        with self._lock:
            self._db.close()
