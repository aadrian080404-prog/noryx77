"""Explicit ownership and dependency policy for the four NORYX fronts."""
from __future__ import annotations

from .boundaries import Front

_ALLOWED: dict[Front, frozenset[Front]] = {
    Front.ORCHESTRATION: frozenset({Front.JARVIS, Front.BROWSER, Front.HYPERSYNTH}),
    Front.JARVIS: frozenset({Front.ORCHESTRATION}),
    Front.BROWSER: frozenset({Front.ORCHESTRATION}),
    Front.HYPERSYNTH: frozenset({Front.ORCHESTRATION}),
}


def allows_dispatch(source: Front, target: Front) -> bool:
    if not isinstance(source, Front) or not isinstance(target, Front):
        raise TypeError("front_required")
    return target in _ALLOWED[source]


def require_dispatch(source: Front, target: Front) -> None:
    if not allows_dispatch(source, target):
        raise PermissionError(f"cross_front_dispatch_denied:{source.value}->{target.value}")
