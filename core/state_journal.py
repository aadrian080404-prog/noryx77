"""Durable, crash-recoverable journal with keyed record authentication.

The HMAC key must be supplied by an external KMS/HSM or protected secret store.
This module detects record tampering and reordering; rollback resistance still
requires a monotonic anchor outside the SQLite rollback domain.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3
from threading import RLock
from typing import Any

from .journal_integrity import (
    AnchorSnapshot,
    JournalAuthenticator,
    JournalRecordProof,
    MonotonicAnchor,
    ZERO_MAC,
)
from .state import NORYXState, StateCommit


class StateJournal:
    """Append-only durable journal authenticated with an externally held HMAC key."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        path: str,
        *,
        integrity_key: bytes,
        key_id: str,
        max_commits: int = 10_000,
        monotonic_anchor: MonotonicAnchor | None = None,
        require_external_anchor: bool = False,
    ) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("journal_path_required")
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits_must_be_positive")
        if not isinstance(require_external_anchor, bool):
            raise ValueError("invalid_external_anchor_requirement")
        if monotonic_anchor is not None and (
            not callable(getattr(monotonic_anchor, "read", None))
            or not callable(getattr(monotonic_anchor, "compare_and_swap", None))
        ):
            raise TypeError("invalid_monotonic_anchor")
        if require_external_anchor and monotonic_anchor is None:
            raise ValueError("external_monotonic_anchor_required")
        self._authenticator = JournalAuthenticator(integrity_key, key_id=key_id)
        self._anchor = monotonic_anchor
        self._require_external_anchor = require_external_anchor
        self.path = path
        self.max_commits = max_commits
        self._lock = RLock()
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS state_commits ("
                "execution_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, state_json TEXT NOT NULL, "
                "verification_stage TEXT NOT NULL, sequence INTEGER NOT NULL UNIQUE, "
                "principal_id TEXT NOT NULL, principal_key_fingerprint TEXT NOT NULL, "
                "record_digest TEXT NOT NULL, schema_version INTEGER NOT NULL, "
                "previous_mac TEXT NOT NULL, record_mac TEXT NOT NULL, key_id TEXT NOT NULL)"
            )
            columns = {row[1] for row in self._db.execute("PRAGMA table_info(state_commits)")}
            required = {
                "execution_id", "task_id", "state_json", "verification_stage", "sequence",
                "principal_id", "principal_key_fingerprint", "record_digest", "schema_version",
                "previous_mac", "record_mac", "key_id",
            }
            if not required.issubset(columns):
                raise RuntimeError("legacy_unkeyed_journal_requires_explicit_migration")
        except Exception:
            self._db.close()
            raise

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
    def _select_columns(cls) -> str:
        return (
            "execution_id,task_id,state_json,verification_stage,sequence,"
            "principal_id,principal_key_fingerprint,record_digest,schema_version,"
            "previous_mac,record_mac,key_id"
        )

    def _from_row(self, row: tuple[Any, ...]) -> StateCommit:
        (execution_id, task_id, state_json, verification_stage, sequence, principal_id,
         fingerprint, digest, schema, previous_mac, record_mac, key_id) = row
        if schema != self.SCHEMA_VERSION:
            raise RuntimeError("unsupported_journal_schema")
        try:
            raw = json.loads(state_json)
            state = NORYXState(**raw)
            commit = StateCommit(
                execution_id, task_id, state, verification_stage, sequence, principal_id, fingerprint
            )
            proof = JournalRecordProof(sequence, previous_mac, digest, key_id, record_mac)
            payload = self._canonical(commit).encode("utf-8")
            if not self._authenticator.verify(proof, payload):
                raise RuntimeError("state_journal_integrity_failure")
            return commit
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("state_journal_integrity_failure") from exc

    @property
    def rollback_protected(self) -> bool:
        return self._anchor is not None

    def _reconcile_anchor_locked(self, rows: list[tuple[Any, ...]]) -> None:
        if self._anchor is None:
            return
        try:
            anchored = self._anchor.read()
        except Exception as exc:
            raise RuntimeError("state_journal_anchor_unavailable") from exc
        if not isinstance(anchored, AnchorSnapshot):
            raise RuntimeError("state_journal_anchor_invalid_snapshot")
        if (
            isinstance(anchored.sequence, bool)
            or not isinstance(anchored.sequence, int)
            or anchored.sequence < 0
            or not isinstance(anchored.mac, str)
            or len(anchored.mac) != 64
        ):
            raise RuntimeError("state_journal_anchor_invalid_snapshot")
        try:
            if len(bytes.fromhex(anchored.mac)) != 32:
                raise ValueError
        except ValueError as exc:
            raise RuntimeError("state_journal_anchor_invalid_snapshot") from exc

        if rows:
            head = AnchorSnapshot(int(rows[-1][4]), rows[-1][10])
        else:
            head = AnchorSnapshot(0, ZERO_MAC)
        if anchored == head:
            return

        # A single DB commit may have completed immediately before process death
        # prevented the external CAS. Repair exactly that one-step gap only.
        if (
            head.sequence == anchored.sequence + 1
            and rows
            and rows[-1][9] == anchored.mac
        ):
            try:
                advanced = self._anchor.compare_and_swap(anchored, head)
                if advanced or self._anchor.read() == head:
                    return
                raise RuntimeError("state_journal_anchor_update_failed")
            except Exception as exc:
                if isinstance(exc, RuntimeError) and str(exc) == "state_journal_anchor_update_failed":
                    raise
                raise RuntimeError("state_journal_anchor_update_failed") from exc
        raise RuntimeError("state_journal_anchor_mismatch")

    def _recover_locked(self) -> dict[str, StateCommit]:
        rows = self._db.execute(
            f"SELECT {self._select_columns()} FROM state_commits ORDER BY sequence"
        ).fetchall()
        commits: dict[str, StateCommit] = {}
        expected_sequence = 1
        previous_mac = ZERO_MAC
        for row in rows:
            commit = self._from_row(row)
            if commit.sequence != expected_sequence:
                raise RuntimeError("state_journal_sequence_gap")
            if row[9] != previous_mac:
                raise RuntimeError("state_journal_chain_discontinuity")
            previous_mac = row[10]
            if commit.execution_id in commits:
                raise RuntimeError("state_journal_duplicate_execution")
            commits[commit.execution_id] = commit
            expected_sequence += 1
        self._reconcile_anchor_locked(rows)
        return commits

    def append(self, commit: StateCommit) -> None:
        if not isinstance(commit, StateCommit):
            raise TypeError("state_commit_required")
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                commits = self._recover_locked()
                if commit.execution_id in commits:
                    raise PermissionError("execution_already_journaled")
                if len(commits) >= self.max_commits:
                    raise MemoryError("journal_capacity_exceeded")
                expected_sequence = len(commits) + 1
                if commit.sequence != expected_sequence:
                    raise RuntimeError("state_journal_sequence_gap")
                previous_mac = ZERO_MAC
                if commits:
                    latest = self._db.execute(
                        "SELECT record_mac FROM state_commits ORDER BY sequence DESC LIMIT 1"
                    ).fetchone()
                    previous_mac = latest[0]
                payload = self._canonical(commit).encode("utf-8")
                proof = self._authenticator.create(commit.sequence, previous_mac, payload)
                state_json = json.dumps(
                    asdict(commit.state), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                self._db.execute(
                    "INSERT INTO state_commits VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        commit.execution_id, commit.task_id, state_json, commit.verification_stage,
                        commit.sequence, commit.principal_id, commit.principal_key_fingerprint,
                        proof.payload_digest, self.SCHEMA_VERSION, proof.previous_mac,
                        proof.mac, proof.key_id,
                    ),
                )
                self._db.execute("COMMIT")
                if self._anchor is not None:
                    rows = self._db.execute(
                        f"SELECT {self._select_columns()} FROM state_commits ORDER BY sequence"
                    ).fetchall()
                    self._reconcile_anchor_locked(rows)
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def get(self, execution_id: str) -> StateCommit | None:
        with self._lock:
            # Validate the full chain before returning an individual record.
            return self._recover_locked().get(execution_id)

    def recover(self) -> dict[str, StateCommit]:
        with self._lock:
            return self._recover_locked()

    def close(self) -> None:
        with self._lock:
            self._db.close()
