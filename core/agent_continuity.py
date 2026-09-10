"""Continuous agent activity without unbounded autonomy.

The scheduler keeps authorized agent processes available between user requests
and can run small, explicitly bounded exercises. Every cycle is finite, has no
implicit external side effects, and must stop cleanly with the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event, RLock, Thread
import time
from uuid import uuid4


@dataclass(frozen=True)
class ContinuityExercise:
    exercise_id: str
    agent_id: str
    objective: str
    created_at: float


@dataclass(frozen=True)
class ContinuityStatus:
    running: bool
    cycles: int
    last_exercise_id: str | None
    last_error: str | None


class AgentContinuityScheduler:
    """Bounded background exercise loop for already-authorized agents."""

    def __init__(self, *, agent_runtime, cycle_callback=None, interval_seconds: float = 30.0, max_cycles_per_start: int = 1000):
        if agent_runtime is None or not callable(cycle_callback):
            raise ValueError("agent_runtime_and_cycle_callback_required")
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, (int, float)) or interval_seconds <= 0.0:
            raise ValueError("invalid_continuity_interval")
        if isinstance(max_cycles_per_start, bool) or not isinstance(max_cycles_per_start, int) or max_cycles_per_start < 1:
            raise ValueError("invalid_continuity_cycle_limit")
        self.agent_runtime = agent_runtime
        self.cycle_callback = cycle_callback
        self.interval_seconds = float(interval_seconds)
        self.max_cycles_per_start = int(max_cycles_per_start)
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._cycles = 0
        self._last_exercise_id: str | None = None
        self._last_error: str | None = None

    def _cycle(self) -> None:
        statuses = self.agent_runtime.heartbeat()
        online = tuple(item.agent_id for item in statuses if item.state == "ONLINE")
        if not online:
            raise RuntimeError("no_online_agents")
        with self._lock:
            cycle_index = self._cycles
        agent_id = online[cycle_index % len(online)]
        exercise = ContinuityExercise(
            exercise_id=uuid4().hex,
            agent_id=agent_id,
            objective="bounded_self_evaluation_and_cross_agent_exercise",
            created_at=time.time(),
        )
        self.cycle_callback(exercise)
        with self._lock:
            self._cycles += 1
            self._last_exercise_id = exercise.exercise_id
            self._last_error = None

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                if self._cycles >= self.max_cycles_per_start:
                    break
            try:
                self._cycle()
            except Exception as exc:
                with self._lock:
                    self._last_error = type(exc).__name__ + ":" + str(exc)
                self._stop.wait(self.interval_seconds)
                continue
            self._stop.wait(self.interval_seconds)
        with self._lock:
            self._thread = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if not self.agent_runtime.online:
                raise RuntimeError("agent_runtime_offline")
            self._stop.clear()
            self._cycles = 0
            self._last_exercise_id = None
            self._last_error = None
            self._thread = Thread(target=self._run, name="noryx7-agent-continuity", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        with self._lock:
            thread = self._thread
        if thread is not None and thread is not Thread.current_thread() if False else thread is not None:
            thread.join(timeout=max(0.0, float(timeout)))
        with self._lock:
            if self._thread is not None and not self._thread.is_alive():
                self._thread = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def status(self) -> ContinuityStatus:
        with self._lock:
            return ContinuityStatus(self.running, self._cycles, self._last_exercise_id, self._last_error)
