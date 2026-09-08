from jarvis.security.audit import AuditLog

def test_empty_audit_log_verifies():
    assert AuditLog().verify()

def test_audit_chain_verifies_after_multiple_events():
    log = AuditLog()
    log.record("request_received", "user", timestamp=1.0)
    log.record("capability_authorized", "user", timestamp=2.0)
    assert log.verify()

def test_audit_tampering_is_detected():
    log = AuditLog()
    log.record("request_received", "user", timestamp=1.0)
    object.__setattr__(log.events[0], "event", "modified")
    assert not log.verify()
