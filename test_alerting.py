import pytest

from .alerting import AlertChannel, AlertRouter, AlertSeverity, EscalationPolicy


def test_verified_warning_routes_to_phone_and_computer():
    alert = AlertRouter().create(
        alert_id="a1", event_id="e1", severity=AlertSeverity.WARNING,
        title="Access attempt", detail="Unauthorized attempt", verified=True,
    )
    assert alert.channels == (AlertChannel.PHONE, AlertChannel.COMPUTER)


def test_critical_call_is_explicitly_opt_in():
    router = AlertRouter(policy=EscalationPolicy(call_on_critical=True))
    alert = router.create(
        alert_id="a2", event_id="e2", severity=AlertSeverity.CRITICAL,
        title="Critical incident", detail="Verified incident", verified=True,
    )
    assert alert.channels == (
        AlertChannel.PHONE, AlertChannel.COMPUTER, AlertChannel.EMERGENCY_CALL
    )


def test_unverified_event_cannot_create_alert():
    with pytest.raises(PermissionError, match="alert_requires_verified_event"):
        AlertRouter().create(
            alert_id="a3", event_id="e3", severity=AlertSeverity.HIGH,
            title="Suspicious", detail="Not verified", verified=False,
        )


def test_alerts_are_immutable_and_recorded():
    router = AlertRouter()
    alert = router.create(
        alert_id="a4", event_id="e4", severity=AlertSeverity.INFO,
        title="Info", detail="Verified", verified=True,
    )
    assert router.alerts() == (alert,)
    with pytest.raises((AttributeError, TypeError)):
        alert.title = "changed"
