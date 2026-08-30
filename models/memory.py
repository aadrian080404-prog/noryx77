from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """Minimal in-memory record for task-relevant information."""

    content: str
    source: str
    associated_task: str = ""


class MemoryStore:
    """Deterministic in-memory store for task-relevant context.

    This is intentionally small and replaceable: later phases can swap the storage
    implementation without changing the orchestrator contract.
    """

    def __init__(self):
        self._entries: list[MemoryEntry] = []

    def store(self, content: str, source: str = "task_result", associated_task: str = "") -> MemoryEntry:
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")

        entry = MemoryEntry(
            content=content.strip(),
            source=source,
            associated_task=associated_task,
        )
        self._entries.append(entry)
        return entry

    def retrieve(self, query: str) -> list[MemoryEntry]:
        """Simple deterministic keyword matching, case-insensitive."""
        if not query:
            return []

        query_tokens = {
            token.lower()
            for token in query.replace("-", " ").split()
            if token.strip()
        }

        if not query_tokens:
            return []

        matches: list[MemoryEntry] = []
        for entry in self._entries:
            entry_text = " ".join(
                [
                    entry.content,
                    entry.source,
                    entry.associated_task,
                ]
            ).lower()
            entry_tokens = {
                token for token in entry_text.replace("-", " ").split() if token.strip()
            }
            if query_tokens & entry_tokens:
                matches.append(entry)
        return matches

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)
