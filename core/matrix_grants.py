"""Durable owner grants for opt-in device contribution.

This is a local persistence adapter. It does not enforce OS resource quotas;
the local supervisor must consume and enforce the current generation.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
import sqlite3
from pathlib import Path
from .matrix_core import ContributionGrant, ResourceVector


@dataclass(frozen=True)
class StoredGrant:
    node_id: str
    owner_id: str
    grant: ContributionGrant


class DurableGrantRegistry:
    def __init__(self, database: str | Path, timeout: float = 5.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("positive_database_timeout_required")
        self.database = str(database)
        self.timeout = float(timeout)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_grants (
                grant_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                generation INTEGER NOT NULL CHECK(generation >= 0),
                cpu_milli INTEGER NOT NULL CHECK(cpu_milli >= 0),
                memory_bytes INTEGER NOT NULL CHECK(memory_bytes >= 0),
                storage_bytes INTEGER NOT NULL CHECK(storage_bytes >= 0),
                bandwidth_bps INTEGER NOT NULL CHECK(bandwidth_bps >= 0),
                allowed_workloads TEXT NOT NULL,
                allow_user_data INTEGER NOT NULL CHECK(allow_user_data IN (0,1))
            )""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _decode(row) -> StoredGrant | None:
        if row is None:
            return None
        grant = ContributionGrant(
            row[0], bool(row[3]), int(row[4]),
            ResourceVector(int(row[5]), int(row[6]), int(row[7]), int(row[8])),
            frozenset(filter(None, row[9].split("\n"))), bool(row[10]),
        )
        return StoredGrant(row[1], row[2], grant)

    def get(self, grant_id: str) -> StoredGrant | None:
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT grant_id,node_id,owner_id,enabled,generation,cpu_milli,
                          memory_bytes,storage_bytes,bandwidth_bps,allowed_workloads,allow_user_data
                   FROM matrix_grants WHERE grant_id=?""", (grant_id,)
            ).fetchone()
        return self._decode(row)

    def put(self, node_id: str, owner_id: str, grant: ContributionGrant) -> StoredGrant:
        if any(not isinstance(value, str) or not value.strip() for value in (node_id, owner_id)):
            raise ValueError("node_and_owner_ids_required")
        if not isinstance(grant, ContributionGrant):
            raise TypeError("contribution_grant_required")
        if any("\n" in value for value in grant.allowed_workloads):
            raise ValueError("workload_class_contains_reserved_delimiter")
        workloads = "\n".join(sorted(grant.allowed_workloads))
        resources = grant.max_resources
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT node_id,owner_id,generation FROM matrix_grants WHERE grant_id=?",
                (grant.grant_id,),
            ).fetchone()
            if previous:
                if previous[0] != node_id or previous[1] != owner_id:
                    raise PermissionError("grant_owner_or_node_binding_immutable")
                if grant.generation <= int(previous[2]):
                    raise PermissionError("grant_generation_must_increase")
            db.execute("""INSERT INTO matrix_grants
                (grant_id,node_id,owner_id,enabled,generation,cpu_milli,memory_bytes,
                 storage_bytes,bandwidth_bps,allowed_workloads,allow_user_data)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(grant_id) DO UPDATE SET
                enabled=excluded.enabled,generation=excluded.generation,
                cpu_milli=excluded.cpu_milli,memory_bytes=excluded.memory_bytes,
                storage_bytes=excluded.storage_bytes,bandwidth_bps=excluded.bandwidth_bps,
                allowed_workloads=excluded.allowed_workloads,allow_user_data=excluded.allow_user_data""",
                (grant.grant_id,node_id,owner_id,int(grant.enabled),grant.generation,
                 resources.cpu_milli,resources.memory_bytes,resources.storage_bytes,
                 resources.bandwidth_bps,workloads,int(grant.allow_user_data)))
            db.commit()
        return StoredGrant(node_id, owner_id, grant)

    def revoke(self, grant_id: str, expected_generation: int) -> StoredGrant:
        if isinstance(expected_generation, bool) or not isinstance(expected_generation, int) or expected_generation < 0:
            raise ValueError("expected_generation_must_be_nonnegative_integer")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT grant_id,node_id,owner_id,enabled,generation,cpu_milli,
                          memory_bytes,storage_bytes,bandwidth_bps,allowed_workloads,allow_user_data
                   FROM matrix_grants WHERE grant_id=?""", (grant_id,)
            ).fetchone()
            current = self._decode(row)
            if current is None:
                raise KeyError("unknown_grant")
            if current.grant.generation != expected_generation:
                raise PermissionError("grant_generation_compare_and_swap_failed")
            next_generation = expected_generation + 1
            db.execute("""UPDATE matrix_grants SET enabled=0,generation=?,cpu_milli=0,
                memory_bytes=0,storage_bytes=0,bandwidth_bps=0,allowed_workloads='',allow_user_data=0
                WHERE grant_id=?""", (next_generation,grant_id))
            db.commit()
        revoked = ContributionGrant(grant_id,False,next_generation,ResourceVector(),frozenset(),False)
        return StoredGrant(current.node_id,current.owner_id,revoked)
