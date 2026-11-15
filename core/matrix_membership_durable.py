"""Crash-recoverable membership epochs and revocation tombstones.

SQLite is local durability only. The injected verifier is responsible for
cryptographic attestation and policy binding; this module is not consensus.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
import math
import sqlite3
from pathlib import Path
from typing import Callable


class MemberState(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class AdmissionEvidence:
    node_id: str
    owner_id: str
    failure_domain: str
    software_measurement: str
    epoch: int
    nonce: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class MemberRecord:
    node_id: str
    owner_id: str
    failure_domain: str
    software_measurement: str
    epoch: int
    capabilities: frozenset[str]
    state: MemberState
    last_nonce: str


class DurableMembershipRegistry:
    """SQLite-backed per-node membership state with monotonic epochs."""

    def __init__(self, database: str | Path, timeout: float = 5.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("positive_database_timeout_required")
        self.database = str(database)
        self.timeout = float(timeout)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_members (
                node_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                failure_domain TEXT NOT NULL,
                software_measurement TEXT NOT NULL,
                epoch INTEGER NOT NULL CHECK(epoch >= 1),
                nonce TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('active','revoked'))
            )""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _decode(row) -> MemberRecord | None:
        if row is None:
            return None
        return MemberRecord(
            row[0], row[1], row[2], row[3], int(row[4]),
            frozenset(filter(None, row[6].split("\n"))),
            MemberState(row[7]), row[5],
        )

    def get(self, node_id: str) -> MemberRecord | None:
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT node_id,owner_id,failure_domain,software_measurement,
                          epoch,nonce,capabilities,state
                   FROM matrix_members WHERE node_id=?""", (node_id,)
            ).fetchone()
        return self._decode(row)

    def admit(self, evidence: AdmissionEvidence, proof: bytes,
              verify: Callable[[AdmissionEvidence, bytes], bool]) -> MemberRecord:
        for value in (evidence.node_id, evidence.owner_id, evidence.failure_domain,
                      evidence.software_measurement, evidence.nonce):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("admission_fields_required")
        if isinstance(evidence.epoch, bool) or not isinstance(evidence.epoch, int) or evidence.epoch < 1:
            raise ValueError("invalid_membership_epoch")
        if not isinstance(proof, bytes) or not proof:
            raise ValueError("attestation_proof_required")
        if not callable(verify):
            raise ValueError("attestation_verifier_required")
        if any(not isinstance(x, str) or not x.strip() or "\n" in x for x in evidence.capabilities):
            raise ValueError("invalid_capability")
        if verify(evidence, proof) is not True:
            raise PermissionError("attestation_verification_failed")
        capabilities = "\n".join(sorted(evidence.capabilities))
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT owner_id,epoch,nonce FROM matrix_members WHERE node_id=?",
                (evidence.node_id,),
            ).fetchone()
            if previous:
                if previous[2] == evidence.nonce:
                    raise PermissionError("admission_nonce_replayed")
                if evidence.epoch <= int(previous[1]):
                    raise PermissionError("membership_epoch_not_monotonic")
                if previous[0] != evidence.owner_id:
                    raise PermissionError("node_owner_change_requires_reenrollment")
            db.execute("""INSERT INTO matrix_members
                (node_id,owner_id,failure_domain,software_measurement,epoch,nonce,capabilities,state)
                VALUES (?,?,?,?,?,?,?,'active')
                ON CONFLICT(node_id) DO UPDATE SET
                owner_id=excluded.owner_id,failure_domain=excluded.failure_domain,
                software_measurement=excluded.software_measurement,epoch=excluded.epoch,
                nonce=excluded.nonce,capabilities=excluded.capabilities,state='active'""",
                (evidence.node_id,evidence.owner_id,evidence.failure_domain,
                 evidence.software_measurement,evidence.epoch,evidence.nonce,capabilities))
            db.commit()
        return MemberRecord(evidence.node_id,evidence.owner_id,evidence.failure_domain,
                            evidence.software_measurement,evidence.epoch,
                            frozenset(evidence.capabilities),MemberState.ACTIVE,evidence.nonce)

    def revoke(self, node_id: str, next_epoch: int) -> MemberRecord:
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id_required")
        if isinstance(next_epoch, bool) or not isinstance(next_epoch, int) or next_epoch < 1:
            raise ValueError("invalid_revocation_epoch")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT node_id,owner_id,failure_domain,software_measurement,
                          epoch,nonce,capabilities,state
                   FROM matrix_members WHERE node_id=?""", (node_id,)
            ).fetchone()
            current = self._decode(row)
            if current is None:
                raise KeyError("unknown_member")
            if next_epoch <= current.epoch:
                raise ValueError("revocation_epoch_must_increase")
            db.execute(
                "UPDATE matrix_members SET epoch=?,capabilities='',state='revoked' WHERE node_id=?",
                (next_epoch,node_id),
            )
            db.commit()
        return MemberRecord(current.node_id,current.owner_id,current.failure_domain,
                            current.software_measurement,next_epoch,frozenset(),
                            MemberState.REVOKED,current.last_nonce)
