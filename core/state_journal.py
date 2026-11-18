"""Durable, crash-recoverable journal for verified NORYX7 state commits.

The journal stores only canonical JSON state snapshots and identity metadata.
SQLite provides transactional durability; the application remains responsible
for choosing a storage location with the required OS/filesystem protections.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
import sqlite3
from threading import RLock
from typing import Any

from .state import NORYXState, StateCommit


class StateJournal:
    """Append-only durable commit journal with replay and tamper checks."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str, *, max_commits: int = 10_000) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("journal_path_required")
        if path == ":memory:":
            raise ValueError("persistent_journal_path_required")
        if isinstance(max_commits, bool) or not isinstance(max_commits, int) or max_commits < 1:
            raise ValueError("max_commits_must_be_positive")
        self.path = path
        self.max_commits = max_commits
        self._lock = RLock()
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS state_commits ("
            "execution_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, state_json TEXT NOT NULL, "
            "verification_stage TEXT NOT NULL, sequence INTEGER NOT NULL UNIQUE, "
            "principal_id TEXT NOT NULL, principal_key_fingerprint TEXT NOT NULL, "
            "record_digest TEXT NOT NULL, schema_version INTEGER NOT NULL)"
        )
        try:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS state_journal_meta "
                "(key TEXT PRIMARY KEY, value INTEGER NOT NULL CHECK(value >= 0))"
            )
            self._db.execute("BEGIN IMMEDIATE")
            for key, value in (
                ("schema_version", self.SCHEMA_VERSION),
                ("max_commits", max_commits),
            ):
                self._db.execute(
                    "INSERT OR IGNORE INTO state_journal_meta(key, value) VALUES (?, ?)",
                    (key, value),
                )
            stored_config = {
                row[0]: row[1]
                for row in self._db.execute(
                    "SELECT key, value FROM state_journal_meta "
                    "WHERE key IN ('schema_version', 'max_commits')"
                ).fetchall()
            }
            if stored_config != {
                "schema_version": self.SCHEMA_VERSION,
                "max_commits": max_commits,
            }:
                raise ValueError("state_journal_configuration_mismatch")
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            self._db.close()
            raise
        try:
            os.chmod(path, 0o600)
        except OSError as exc:
            self._db.close()
            raise RuntimeError("state_journal_permissions_unavailable") from exc

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

    def append(self, commit: StateCommit) -> None:
        if not isinstance(commit, StateCommit):
            raise TypeError("state_commit_required")
        if (
            isinstance(commit.sequence, bool)
            or not isinstance(commit.sequence, int)
            or commit.sequence < 1
        ):
            raise ValueError("invalid_state_commit_sequence")
        digest = self._digest(commit)
        state_json = json.dumps(
            asdict(commit.state), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                if self._db.execute(
                    "SELECT 1 FROM state_commits WHERE execution_id=?",
                    (commit.execution_id,),
                ).fetchone():
                    raise PermissionError("execution_already_journaled")
                count = self._db.execute(
                    "SELECT COUNT(*) FROM state_commits"
                ).fetchone()[0]
                if count >= self.max_commits:
                    raise MemoryError("journal_capacity_exceeded")
                latest_sequence = self._db.execute(
                    "SELECT COALESCE(MAX(sequence), 0) FROM state_commits"
                ).fetchone()[0]
                if commit.sequence != latest_sequence + 1:
                    raise RuntimeError("state_journal_sequence_conflict")
                self._db.execute(
                    "INSERT INTO state_commits VALUES (?,?,?,?,?,?,?,?,?)",
                    (commit.execution_id, commit.task_id, state_json, commit.verification_stage,
                     commit.sequence, commit.principal_id, commit.principal_key_fingerprint,
                     digest, self.SCHEMA_VERSION),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
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
