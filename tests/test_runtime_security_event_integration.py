import pytest

from core.durable_security_events import DurableSecurityEventBus
from core.observability import EventKind, SecurityEventBus
from noryx7_runtime.contracts import Intent, PlanStep, ExecutionStatus
from noryx7_runtime.engine import RuntimeEngine


KEY = b"runtime-security-event-integration-key-at-least-32-bytes"


def open_bus(path):
    return DurableSecurityEventBus(str(path), integrity_key=KEY, key_id="runtime-events-v1")


def test_strict_runtime_mode_requires_durable_security_event_bus(tmp_path):
    with pytest.raises(ValueError, match="durable_security_event_bus_required"):
        RuntimeEngine(require_durable_security_events=True)
    with pytest.raises(ValueError, match="durable_security_event_bus_required"):
        RuntimeEngine(
            security_event_bus=SecurityEventBus(),
            require_durable_security_events=True,
        )
    bus = open_bus(tmp_path / "events.sqlite")
    engine = RuntimeEngine(security_event_bus=bus, require_durable_security_events=True)
    assert engine.runtime_id
    bus.close()


def test_executor_failure_is_written_to_durable_event_stream(tmp_path):
    bus = open_bus(tmp_path / "events.sqlite")
    engine = RuntimeEngine(security_event_bus=bus, require_durable_security_events=True)

    def broken_executor(envelope):
        raise RuntimeError("private details are not persisted")

    result = engine.execute(
        Intent("perform a test", "principal-1"),
        [PlanStep("step-1", "local.test", "local", {})],
        executor=broken_executor,
        verifier=lambda envelope, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    events = bus.snapshot()
    assert len(events) == 1
    assert events[0].kind is EventKind.PROCESS_ANOMALY
    assert events[0].component == "runtime"
    bus.close()


def test_high_risk_authorization_denial_is_audited(tmp_path):
    bus = open_bus(tmp_path / "events.sqlite")
    engine = RuntimeEngine(security_event_bus=bus, require_durable_security_events=True)
    result = engine.execute(
        Intent("perform privileged test", "principal-1"),
        [PlanStep("step-1", "system_change", "local", {}, risk_class="high")],
        executor=lambda envelope: True,
        verifier=lambda envelope, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert bus.snapshot()[0].kind is EventKind.AUTH_FAILURE
    bus.close()


def test_verification_failure_is_audited(tmp_path):
    bus = open_bus(tmp_path / "events.sqlite")
    engine = RuntimeEngine(security_event_bus=bus, require_durable_security_events=True)
    result = engine.execute(
        Intent("perform test", "principal-1"),
        [PlanStep("step-1", "local.test", "local", {})],
        executor=lambda envelope: {"untrusted": True},
        verifier=lambda envelope, output: False,
    )
    assert result.status is ExecutionStatus.REJECTED
    assert bus.snapshot()[0].kind is EventKind.INTEGRITY_VIOLATION
    bus.close()


def test_closed_durable_event_bus_denies_high_risk_authorization(tmp_path):
    bus = open_bus(tmp_path / "events.sqlite")
    engine = RuntimeEngine(security_event_bus=bus, require_durable_security_events=True)
    bus.close()
    result = engine.execute(
        Intent("perform privileged test", "principal-1"),
        [PlanStep("step-1", "system_change", "local", {}, risk_class="high")],
        executor=lambda envelope: True,
        verifier=lambda envelope, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "security_event_persistence_failed"
