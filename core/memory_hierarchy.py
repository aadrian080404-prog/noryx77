"""Thread-safe bounded L0-L5 memory hierarchy.

This is a process-local hierarchy/index. It does not replicate data between
devices or nodes and makes no distributed-consistency claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from threading import RLock


class MemoryLevel(IntEnum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: str
    level: MemoryLevel


class MemoryHierarchy:
    MAX_KEY_BYTES = 1024
    MAX_VALUE_CHARS = 1_000_000
    MAX_CAPACITY = 1_000_000

    def __init__(self, max_records: int = 100_000):
        if isinstance(max_records, bool) or not isinstance(max_records, int) or not 1 <= max_records <= self.MAX_CAPACITY:
            raise ValueError("invalid_memory_capacity")
        self._max = max_records
        self._data: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    @classmethod
    def _valid_key(cls, key: object) -> bool:
        return isinstance(key, str) and bool(key.strip()) and len(key.encode("utf-8")) <= cls.MAX_KEY_BYTES

    @classmethod
    def _validate_record(cls, record: object) -> MemoryRecord:
        if not isinstance(record, MemoryRecord):
            raise TypeError("memory_record_required")
        if not cls._valid_key(record.key):
            raise ValueError("invalid_memory_key")
        if not isinstance(record.value, str) or len(record.value) > cls.MAX_VALUE_CHARS:
            raise ValueError("invalid_memory_value")
        if not isinstance(record.level, MemoryLevel):
            raise ValueError("invalid_memory_level")
        return record

    def put(self, record: MemoryRecord) -> None:
        record = self._validate_record(record)
        with self._lock:
            if record.key not in self._data and len(self._data) >= self._max:
                raise MemoryError("memory_capacity_reached")
            self._data[record.key] = record

    def get(self, key: str) -> MemoryRecord | None:
        if not self._valid_key(key):
            return None
        with self._lock:
            return self._data.get(key)

    def promote(self, key: str, level: MemoryLevel) -> MemoryRecord:
        if not self._valid_key(key):
            raise ValueError("invalid_memory_key")
        if not isinstance(level, MemoryLevel):
            raise ValueError("invalid_memory_level")
        with self._lock:
            old = self._data.get(key)
            if old is None:
                raise KeyError(key)
            updated = MemoryRecord(old.key, old.value, level)
            self._data[key] = updated
            return updated

    def delete(self, key: str) -> bool:
        if not self._valid_key(key):
            return False
        with self._lock:
            return self._data.pop(key, None) is not None

    def snapshot(self) -> tuple[MemoryRecord, ...]:
        with self._lock:
            return tuple(self._data[key] for key in sorted(self._data))

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
