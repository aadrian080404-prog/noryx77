import sqlite3

import pytest

from core.durable_security_events import DurableSecurityEventBus
from core.observability import EventKind


KEY = b"durable-security-events-test-key-material-32-bytes"
KEY_ID = "security-event-kms-v1"


def open_bus(path):
    return DurableSecurityEventBus(str(path), integrity_key=KEY, key_id=KEY_ID)


def test_security_events_survive_restart(tmp_path):
    path = tmp_path / "events.sqlite"
    bus = open_bus(path)
    first = bus.publish(EventKind.AUTH_FAILURE, component="identity", severity=70, evidence_digest="a" * 64)
    second = bus.publish(EventKind.OUTBOUND_ANOMALY, component="egress", severity=90, evidence_digest="b" * 64)
    assert (first.event_id, second.event_id) == (1, 2)
    bus.close()

    recovered = open_bus(path)
    events = recovered.snapshot()
    assert len(events) == 2
    assert events[0].kind is EventKind.AUTH_FAILURE
    assert events[1].component == "egress"
    recovered.close()


def test_tampered_security_event_fails_closed(tmp_path):
    path = tmp_path / "events.sqlite"
    bus = open_bus(path)
    bus.publish(EventKind.AUTH_FAILURE, component="identity", severity=70, evidence_digest="a" * 64)
    bus.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE security_events SET event_json=? WHERE sequence=1",
               ('{"component":"identity","evidence_digest":"' + "a" * 64 + '","kind":"policy_violation","severity":1,"timestamp":1.0}',))
    db.commit()
    db.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        open_bus(path)


def test_closed_security_event_bus_rejects_publish(tmp_path):
    bus = open_bus(tmp_path / "events.sqlite")
    assert bus.durable
    bus.close()
    assert not bus.durable
    with pytest.raises(RuntimeError, match="failed_closed"):
        bus.publish(EventKind.AUTH_FAILURE, component="identity", severity=70, evidence_digest="a" * 64)
