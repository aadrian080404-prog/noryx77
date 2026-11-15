"""Crash-recoverable node-local resource reservations.

The database is the local reservation authority for one node. It is not a
cross-node scheduler, OS sandbox, or distributed consensus protocol.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
import math
import sqlite3
from pathlib import Path
from .matrix_core import NodeProfile, ResourceVector, WorkloadRequest, eligible


@dataclass(frozen=True)
class DurableReservation:
    node_id: str
    task_id: str
    workload_class: str
    grant_generation: int
    resources: ResourceVector


@dataclass(frozen=True)
class DurableStopIntent:
    node_id: str
    task_id: str
    grant_generation: int
    status: str


class DurableReservationBook:
    def __init__(self, database: str | Path, node: NodeProfile, timeout: float = 5.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("positive_database_timeout_required")
        self.database = str(database)
        self.timeout = float(timeout)
        self.node = node
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_reservation_state (
                node_id TEXT PRIMARY KEY, grant_id TEXT NOT NULL, generation INTEGER NOT NULL,
                capacity_cpu INTEGER NOT NULL, capacity_memory INTEGER NOT NULL,
                capacity_storage INTEGER NOT NULL, capacity_bandwidth INTEGER NOT NULL,
                committed_cpu INTEGER NOT NULL, committed_memory INTEGER NOT NULL,
                committed_storage INTEGER NOT NULL, committed_bandwidth INTEGER NOT NULL,
                reserve_cpu INTEGER NOT NULL, reserve_memory INTEGER NOT NULL,
                reserve_storage INTEGER NOT NULL, reserve_bandwidth INTEGER NOT NULL,
                max_cpu INTEGER NOT NULL, max_memory INTEGER NOT NULL,
                max_storage INTEGER NOT NULL, max_bandwidth INTEGER NOT NULL,
                enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_reservations (
                node_id TEXT NOT NULL, task_id TEXT NOT NULL, workload_class TEXT NOT NULL,
                grant_generation INTEGER NOT NULL, cpu INTEGER NOT NULL, memory INTEGER NOT NULL,
                storage INTEGER NOT NULL, bandwidth INTEGER NOT NULL,
                PRIMARY KEY(node_id,task_id),
                FOREIGN KEY(node_id) REFERENCES matrix_reservation_state(node_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_stop_intents (
                node_id TEXT NOT NULL, task_id TEXT NOT NULL,
                grant_generation INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared','pending')),
                PRIMARY KEY(node_id,task_id)
            )""")
            db.execute("BEGIN IMMEDIATE")
            snapshot = self._snapshot(node)
            existing = db.execute(
                "SELECT * FROM matrix_reservation_state WHERE node_id=?", (node.node_id,)
            ).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO matrix_reservation_state VALUES (" + ",".join("?" for _ in snapshot) + ")",
                    snapshot,
                )
            elif tuple(existing) != snapshot:
                raise PermissionError("reservation_state_mismatch_requires_explicit_reconciliation")
            db.commit()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _snapshot(node: NodeProfile) -> tuple:
        c, u, r, g = node.envelope.capacity, node.envelope.committed, node.envelope.reserve, node.grant
        return (node.node_id,g.grant_id,g.generation,
                c.cpu_milli,c.memory_bytes,c.storage_bytes,c.bandwidth_bps,
                u.cpu_milli,u.memory_bytes,u.storage_bytes,u.bandwidth_bps,
                r.cpu_milli,r.memory_bytes,r.storage_bytes,r.bandwidth_bps,
                g.max_resources.cpu_milli,g.max_resources.memory_bytes,
                g.max_resources.storage_bytes,g.max_resources.bandwidth_bps,int(g.enabled))

    @staticmethod
    def _vector(row: tuple) -> ResourceVector:
        return ResourceVector(int(row[0]),int(row[1]),int(row[2]),int(row[3]))

    def list(self) -> tuple[DurableReservation, ...]:
        with closing(self._connect()) as db:
            rows = db.execute(
                """SELECT node_id,task_id,workload_class,grant_generation,cpu,memory,storage,bandwidth
                   FROM matrix_reservations WHERE node_id=? ORDER BY task_id""",
                (self.node.node_id,),
            ).fetchall()
        return tuple(DurableReservation(row[0],row[1],row[2],int(row[3]),
                                        self._vector(row[4:8])) for row in rows)

    def prepare_stop_intents(self) -> tuple[DurableStopIntent, ...]:
        """Durably record every reservation as a prepared drain before revocation."""
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            # Fence admission in the same SQLite write transaction that snapshots
            # current reservations. Other supervisor processes share this gate.
            db.execute(
                "UPDATE matrix_reservation_state SET enabled=0 "
                "WHERE node_id=? AND generation=?",
                (self.node.node_id, self.node.grant.generation),
            )
            rows = db.execute(
                """SELECT task_id,grant_generation FROM matrix_reservations
                   WHERE node_id=? ORDER BY task_id""", (self.node.node_id,)
            ).fetchall()
            for task_id, generation in rows:
                db.execute(
                    """INSERT INTO matrix_stop_intents(node_id,task_id,grant_generation,status)
                       VALUES(?,?,?,'prepared')
                       ON CONFLICT(node_id,task_id) DO NOTHING""",
                    (self.node.node_id, task_id, int(generation)),
                )
            db.commit()
        return self.list_stop_intents()

    def activate_stop_intents(self) -> tuple[DurableStopIntent, ...]:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE matrix_stop_intents SET status='pending' WHERE node_id=? AND status='prepared'",
                (self.node.node_id,),
            )
            db.commit()
        return self.list_stop_intents()

    def cancel_prepared_stop_intents(self) -> None:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "DELETE FROM matrix_stop_intents WHERE node_id=? AND status='prepared'",
                (self.node.node_id,),
            )
            # Roll back the admission fence only when the original grant is still
            # enabled and no earlier durable stop remains pending.
            db.execute(
                """UPDATE matrix_reservation_state SET enabled=1
                   WHERE node_id=? AND generation=? AND ?=1 AND NOT EXISTS (
                       SELECT 1 FROM matrix_stop_intents
                       WHERE node_id=? AND status='pending'
                   )""",
                (self.node.node_id, self.node.grant.generation,
                 int(self.node.grant.enabled), self.node.node_id),
            )
            db.commit()

    def recover_prepared_stop_intents(self, current_generation: int | None, grant_enabled: bool) -> tuple[DurableStopIntent, ...]:
        """Resolve a crash between durable intent preparation and grant update."""
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT task_id,grant_generation FROM matrix_stop_intents
                   WHERE node_id=? AND status='prepared'""", (self.node.node_id,)
            ).fetchall()
            for task_id, generation in rows:
                if current_generation is None or current_generation > int(generation) or not grant_enabled:
                    db.execute(
                        """UPDATE matrix_stop_intents SET status='pending'
                           WHERE node_id=? AND task_id=?""",
                        (self.node.node_id, task_id),
                    )
                else:
                    db.execute(
                        "DELETE FROM matrix_stop_intents WHERE node_id=? AND task_id=?",
                        (self.node.node_id, task_id),
                    )
            # Recover the admission gate even when the crash happened before any
            # reservation existed (and therefore no stop-intent row was written).
            # A stale or revoked grant must never reopen admission.
            can_reopen = (
                grant_enabled
                and current_generation is not None
                and current_generation == self.node.grant.generation
            )
            db.execute(
                """UPDATE matrix_reservation_state
                   SET enabled=CASE WHEN ?=1 AND NOT EXISTS (
                       SELECT 1 FROM matrix_stop_intents
                       WHERE node_id=? AND status='pending'
                   ) THEN 1 ELSE 0 END
                   WHERE node_id=?""",
                (int(can_reopen), self.node.node_id, self.node.node_id),
            )
            db.commit()
        return self.list_stop_intents()

    def list_stop_intents(self) -> tuple[DurableStopIntent, ...]:
        with closing(self._connect()) as db:
            rows = db.execute(
                """SELECT node_id,task_id,grant_generation,status FROM matrix_stop_intents
                   WHERE node_id=? ORDER BY task_id""", (self.node.node_id,)
            ).fetchall()
        return tuple(DurableStopIntent(row[0], row[1], int(row[2]), row[3]) for row in rows)

    def acknowledge_stop_intent(self, task_id: str, generation: int) -> None:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """DELETE FROM matrix_stop_intents
                   WHERE node_id=? AND task_id=? AND grant_generation=? AND status='pending'""",
                (self.node.node_id, task_id, generation),
            )
            db.execute(
                "DELETE FROM matrix_reservations WHERE node_id=? AND task_id=? AND grant_generation=?",
                (self.node.node_id, task_id, generation),
            )
            db.commit()

    def reserve(self, request: WorkloadRequest) -> DurableReservation:
        if not eligible(self.node, request):
            raise PermissionError("node_not_eligible_for_workload")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute(
                "SELECT generation,enabled,max_cpu,max_memory,max_storage,max_bandwidth,"
                "capacity_cpu,capacity_memory,capacity_storage,capacity_bandwidth,"
                "committed_cpu,committed_memory,committed_storage,committed_bandwidth,"
                "reserve_cpu,reserve_memory,reserve_storage,reserve_bandwidth "
                "FROM matrix_reservation_state WHERE node_id=?",
                (self.node.node_id,),
            ).fetchone()
            if state is None or int(state[0]) != self.node.grant.generation or not bool(state[1]):
                raise PermissionError("durable_grant_generation_or_state_mismatch")
            if request.generation != int(state[0]):
                raise PermissionError("stale_workload_grant_generation")
            previous = db.execute(
                "SELECT 1 FROM matrix_reservations WHERE node_id=? AND task_id=?",
                (self.node.node_id,request.task_id),
            ).fetchone()
            if previous:
                raise ValueError("task_already_reserved")
            rows = db.execute(
                "SELECT cpu,memory,storage,bandwidth FROM matrix_reservations WHERE node_id=?",
                (self.node.node_id,),
            ).fetchall()
            active = ResourceVector()
            for row in rows:
                active = active + self._vector(row)
            if not (active + request.resources).fits_within(self._vector(state[2:6])):
                raise PermissionError("owner_contribution_quota_exceeded")
            available = self._vector(state[6:10]) - self._vector(state[10:14]) - self._vector(state[14:18]) - active
            if not request.resources.fits_within(available):
                raise PermissionError("resource_reserve_unavailable")
            db.execute(
                """INSERT INTO matrix_reservations
                   (node_id,task_id,workload_class,grant_generation,cpu,memory,storage,bandwidth)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (self.node.node_id,request.task_id,request.workload_class,request.generation,
                 request.resources.cpu_milli,request.resources.memory_bytes,
                 request.resources.storage_bytes,request.resources.bandwidth_bps),
            )
            db.commit()
        return DurableReservation(self.node.node_id,request.task_id,request.workload_class,
                                  request.generation,request.resources)

    def release(self, task_id: str) -> DurableReservation:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT node_id,task_id,workload_class,grant_generation,cpu,memory,storage,bandwidth
                   FROM matrix_reservations WHERE node_id=? AND task_id=?""",
                (self.node.node_id,task_id),
            ).fetchone()
            if row is None:
                raise KeyError("unknown_reservation")
            db.execute("DELETE FROM matrix_reservations WHERE node_id=? AND task_id=?",
                       (self.node.node_id,task_id))
            db.commit()
        return DurableReservation(row[0],row[1],row[2],int(row[3]),self._vector(row[4:8]))

    def reconcile_grant(self, new_node: NodeProfile) -> tuple[str, ...]:
        if new_node.node_id != self.node.node_id or new_node.grant.grant_id != self.node.grant.grant_id:
            raise ValueError("node_or_grant_identity_mismatch")
        if new_node.grant.generation <= self.node.grant.generation:
            raise ValueError("grant_generation_must_increase")
        old = self._snapshot(self.node)
        new = self._snapshot(new_node)
        # Resource baseline must be identical; only grant authority may change here.
        if old[3:15] != new[3:15]:
            raise ValueError("resource_baseline_change_requires_reprovisioning")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM matrix_reservation_state WHERE node_id=?", (self.node.node_id,)
            ).fetchone()
            # prepare_stop_intents() deliberately flips only the durable enabled
            # bit to fence concurrent admissions before grant revocation.
            expected_fenced = old[:-1] + (0,)
            if current is None or tuple(current) not in (old, expected_fenced):
                raise PermissionError("reservation_state_changed_requires_refresh")
            cancelled = tuple(row[0] for row in db.execute(
                "SELECT task_id FROM matrix_reservations WHERE node_id=? ORDER BY task_id",
                (self.node.node_id,),
            ).fetchall())
            db.execute("DELETE FROM matrix_reservations WHERE node_id=?", (self.node.node_id,))
            db.execute(
                "UPDATE matrix_reservation_state SET grant_id=?,generation=?,max_cpu=?,max_memory=?,"
                "max_storage=?,max_bandwidth=?,enabled=? WHERE node_id=?",
                (new_node.grant.grant_id,new_node.grant.generation,
                 new_node.grant.max_resources.cpu_milli,new_node.grant.max_resources.memory_bytes,
                 new_node.grant.max_resources.storage_bytes,new_node.grant.max_resources.bandwidth_bps,
                 int(new_node.grant.enabled),self.node.node_id),
            )
            db.commit()
        self.node = new_node
        return cancelled
