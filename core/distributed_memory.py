"""Offline-first causal replication for NORYX7 memory.

This module defines a transport-neutral SQLite event log. It provides
idempotent exchange, vector-clock causality, deterministic conflict selection,
and tombstones. Transport authentication and global anti-rollback remain
deployment responsibilities; this is not a consensus protocol.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Mapping, Sequence

MAX_ACTOR_ID = 256
MAX_MEMORY_KEY = 1024
MAX_MEMORY_VALUE = 1_000_000
MAX_CLOCK_ACTORS = 4096
MAX_BATCH_EVENTS = 10000
_DOMAIN = b"NORYX7/DISTRIBUTED_MEMORY_EVENT/v1\x00"


@dataclass(frozen=True)
class MemoryEvent:
    actor_id: str
    counter: int
    key: str
    value: str | None
    deleted: bool
    clock: tuple[tuple[str, int], ...]

    def validate(self) -> None:
        if not isinstance(self.actor_id, str) or not self.actor_id.strip() or len(self.actor_id.encode()) > MAX_ACTOR_ID:
            raise ValueError("invalid_memory_actor")
        if isinstance(self.counter, bool) or not isinstance(self.counter, int) or self.counter < 1:
            raise ValueError("invalid_memory_counter")
        if not isinstance(self.key, str) or not self.key or len(self.key.encode()) > MAX_MEMORY_KEY:
            raise ValueError("invalid_memory_key")
        if not isinstance(self.deleted, bool):
            raise ValueError("invalid_memory_tombstone")
        if self.deleted:
            if self.value is not None:
                raise ValueError("deleted_memory_event_must_not_have_value")
        elif not isinstance(self.value, str) or len(self.value.encode()) > MAX_MEMORY_VALUE:
            raise ValueError("invalid_memory_value")
        if not isinstance(self.clock, tuple) or len(self.clock) > MAX_CLOCK_ACTORS:
            raise ValueError("invalid_memory_vector_clock")
        seen: set[str] = set()
        for actor, count in self.clock:
            if not isinstance(actor, str) or not actor.strip() or len(actor.encode()) > MAX_ACTOR_ID or actor in seen:
                raise ValueError("invalid_memory_vector_clock_actor")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("invalid_memory_vector_clock_counter")
            seen.add(actor)
        clock = dict(self.clock)
        if clock.get(self.actor_id) != self.counter:
            raise ValueError("memory_event_clock_mismatch")
        if tuple(sorted(self.clock)) != self.clock:
            raise ValueError("memory_vector_clock_must_be_canonical")


@dataclass(frozen=True)
class MemoryConflict:
    key: str
    winner: MemoryEvent
    concurrent: tuple[MemoryEvent, ...]


def _canonical(event: MemoryEvent) -> bytes:
    event.validate()
    payload = {
        "actor_id": event.actor_id,
        "counter": event.counter,
        "key": event.key,
        "value": event.value,
        "deleted": event.deleted,
        "clock": [[actor, count] for actor, count in event.clock],
    }
    return _DOMAIN + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _event_id(event: MemoryEvent) -> str:
    return hashlib.sha256(_canonical(event)).hexdigest()


def _dominates(left: MemoryEvent, right: MemoryEvent) -> bool:
    a, b = dict(left.clock), dict(right.clock)
    actors = set(a) | set(b)
    return all(a.get(actor, 0) >= b.get(actor, 0) for actor in actors) and any(
        a.get(actor, 0) > b.get(actor, 0) for actor in actors
    )


def _event_order(event: MemoryEvent) -> tuple[int, str, str]:
    return (event.counter, event.actor_id, _event_id(event))


class DistributedMemoryStore:
    """SQLite-backed causal event store with deterministic offline merge.

    A node has one stable actor_id. Export batches are immutable events;
    receivers validate and de-duplicate them. Concurrent writes are retained
    in the log and surfaced as conflicts instead of being silently discarded.
    """

    def __init__(self, database_path: str, *, actor_id: str) -> None:
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id.encode()) > MAX_ACTOR_ID:
            raise ValueError("invalid_memory_actor")
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("memory_database_path_required")
        self.actor_id = actor_id
        self._lock = threading.RLock()
        self._closed = False
        self._db = sqlite3.connect(str(Path(database_path)), timeout=30, isolation_level=None, check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS memory_events ("
                "event_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, counter INTEGER NOT NULL, "
                "memory_key TEXT NOT NULL, payload TEXT NOT NULL, "
                "UNIQUE(actor_id,counter))"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS memory_node_meta ("
                "meta_key TEXT PRIMARY KEY, meta_value TEXT NOT NULL)"
            )
            self._db.execute(
                "INSERT OR IGNORE INTO memory_node_meta(meta_key,meta_value) VALUES('actor_id',?)",
                (actor_id,),
            )
            stored_actor = self._db.execute(
                "SELECT meta_value FROM memory_node_meta WHERE meta_key='actor_id'"
            ).fetchone()[0]
            if stored_actor != actor_id:
                raise ValueError("memory_database_actor_mismatch")
            self._load_events()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("distributed_memory_closed")

    @staticmethod
    def _decode(payload: str) -> MemoryEvent:
        raw = json.loads(payload)
        event = MemoryEvent(
            actor_id=raw["actor_id"], counter=raw["counter"], key=raw["key"],
            value=raw["value"], deleted=raw["deleted"],
            clock=tuple((item[0], item[1]) for item in raw["clock"]),
        )
        event.validate()
        return event

    def _load_events(self) -> tuple[MemoryEvent, ...]:
        rows = self._db.execute("SELECT event_id,payload FROM memory_events ORDER BY actor_id,counter").fetchall()
        events = []
        for stored_id, payload in rows:
            event = self._decode(payload)
            if _event_id(event) != stored_id:
                raise RuntimeError("memory_event_integrity_failure")
            events.append(event)
        return tuple(events)

    def _all_events(self) -> tuple[MemoryEvent, ...]:
        return self._load_events()

    def _next_event(self, key: str, value: str | None, deleted: bool) -> MemoryEvent:
        events = self._all_events()
        clock: dict[str, int] = {}
        for event in events:
            for actor, counter in event.clock:
                clock[actor] = max(clock.get(actor, 0), counter)
        counter = clock.get(self.actor_id, 0) + 1
        clock[self.actor_id] = counter
        return MemoryEvent(self.actor_id, counter, key, value, deleted, tuple(sorted(clock.items())))

    def write(self, key: str, value: str) -> MemoryEvent:
        if not isinstance(value, str):
            raise ValueError("invalid_memory_value")
        return self._append_local(key, value, False)

    def delete(self, key: str) -> MemoryEvent:
        return self._append_local(key, None, True)

    def _append_local(self, key: str, value: str | None, deleted: bool) -> MemoryEvent:
        # Validate the proposed fields before opening a transaction.
        probe = MemoryEvent(self.actor_id, 1, key, value, deleted, ((self.actor_id, 1),))
        probe.validate()
        with self._lock:
            self._ensure_open()
            self._db.execute("BEGIN IMMEDIATE")
            try:
                event = self._next_event(key, value, deleted)
                self._insert_event(event)
                self._db.execute("COMMIT")
                return event
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def _insert_event(self, event: MemoryEvent) -> bool:
        event.validate()
        payload = json.dumps({
            "actor_id": event.actor_id, "counter": event.counter, "key": event.key,
            "value": event.value, "deleted": event.deleted,
            "clock": [[a, c] for a, c in event.clock],
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        digest = _event_id(event)
        existing = self._db.execute(
            "SELECT event_id FROM memory_events WHERE actor_id=? AND counter=?",
            (event.actor_id, event.counter),
        ).fetchone()
        if existing is not None:
            if existing[0] != digest:
                raise ValueError("memory_actor_counter_equivocation")
            return False
        self._db.execute(
            "INSERT INTO memory_events(event_id,actor_id,counter,memory_key,payload) VALUES(?,?,?,?,?)",
            (digest, event.actor_id, event.counter, event.key, payload),
        )
        return True

    def export_since(self, peer_clock: Mapping[str, int], *, limit: int = MAX_BATCH_EVENTS) -> tuple[MemoryEvent, ...]:
        if not isinstance(peer_clock, Mapping) or len(peer_clock) > MAX_CLOCK_ACTORS:
            raise ValueError("invalid_peer_vector_clock")
        normalized: dict[str, int] = {}
        for actor, counter in peer_clock.items():
            if not isinstance(actor, str) or not actor.strip() or isinstance(counter, bool) or not isinstance(counter, int) or counter < 0:
                raise ValueError("invalid_peer_vector_clock")
            normalized[actor] = counter
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_BATCH_EVENTS:
            raise ValueError("invalid_memory_batch_limit")
        with self._lock:
            self._ensure_open()
            pending = [e for e in self._all_events() if e.counter > normalized.get(e.actor_id, 0)]
            pending.sort(key=lambda e: (e.actor_id, e.counter))
            return tuple(pending[:limit])

    def merge(self, events: Sequence[MemoryEvent]) -> int:
        if isinstance(events, (str, bytes)) or not isinstance(events, Sequence) or len(events) > MAX_BATCH_EVENTS:
            raise ValueError("invalid_memory_replication_batch")
        validated: list[MemoryEvent] = []
        seen: dict[tuple[str, int], str] = {}
        for event in events:
            event.validate()
            identity = (event.actor_id, event.counter)
            digest = _event_id(event)
            if identity in seen and seen[identity] != digest:
                raise ValueError("memory_batch_equivocation")
            seen[identity] = digest
            validated.append(event)
        with self._lock:
            self._ensure_open()
            self._db.execute("BEGIN IMMEDIATE")
            try:
                # A signed peer may still omit an earlier actor event. Enforce
                # contiguous per-actor counters so later events cannot make a
                # missing history segment look complete.
                maxima = {
                    actor: int(counter)
                    for actor, counter in self._db.execute(
                        "SELECT actor_id,MAX(counter) FROM memory_events GROUP BY actor_id"
                    ).fetchall()
                }
                pending: dict[tuple[str, int], MemoryEvent] = {}
                for event in validated:
                    existing = self._db.execute(
                        "SELECT event_id FROM memory_events WHERE actor_id=? AND counter=?",
                        (event.actor_id, event.counter),
                    ).fetchone()
                    if existing is not None:
                        if existing[0] != _event_id(event):
                            raise ValueError("memory_actor_counter_equivocation")
                        continue
                    pending[(event.actor_id, event.counter)] = event

                # Per-actor continuity is necessary but not sufficient: every
                # cross-actor vector-clock dependency must also exist locally
                # or be supplied earlier in this same atomic batch.
                inserted = 0
                while pending:
                    ready = []
                    for identity, event in pending.items():
                        expected = maxima.get(event.actor_id, 0) + 1
                        if event.counter != expected:
                            continue
                        dependencies_present = all(
                            actor == event.actor_id
                            or maxima.get(actor, 0) >= counter
                            for actor, counter in event.clock
                        )
                        if dependencies_present:
                            ready.append((identity, event))
                    if not ready:
                        actor_gaps = any(
                            (actor, maxima.get(actor, 0) + 1) not in pending
                            for actor, counter in pending
                            if counter > maxima.get(actor, 0) + 1
                        )
                        if actor_gaps:
                            raise ValueError("memory_actor_counter_gap")
                        raise ValueError("memory_causal_dependency_missing")
                    ready.sort(key=lambda item: (item[1].actor_id, item[1].counter))
                    for identity, event in ready:
                        if self._insert_event(event):
                            inserted += 1
                        maxima[event.actor_id] = event.counter
                        pending.pop(identity)
                self._db.execute("COMMIT")
                return inserted
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def vector_clock(self) -> dict[str, int]:
        with self._lock:
            self._ensure_open()
            result: dict[str, int] = {}
            for event in self._all_events():
                for actor, counter in event.clock:
                    result[actor] = max(result.get(actor, 0), counter)
            return dict(sorted(result.items()))

    def read(self, key: str) -> MemoryEvent | None:
        if not isinstance(key, str) or not key:
            raise ValueError("invalid_memory_key")
        with self._lock:
            self._ensure_open()
            candidates = [event for event in self._all_events() if event.key == key]
            if not candidates:
                return None
            maximal = [event for event in candidates if not any(_dominates(other, event) for other in candidates if other is not event)]
            winner = max(maximal, key=_event_order)
            return None if winner.deleted else winner

    def conflicts(self, key: str) -> MemoryConflict | None:
        if not isinstance(key, str) or not key:
            raise ValueError("invalid_memory_key")
        with self._lock:
            self._ensure_open()
            candidates = [event for event in self._all_events() if event.key == key]
            maximal = [event for event in candidates if not any(_dominates(other, event) for other in candidates if other is not event)]
            if len(maximal) < 2:
                return None
            winner = max(maximal, key=_event_order)
            return MemoryConflict(key, winner, tuple(sorted((e for e in maximal if e != winner), key=_event_order)))

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
