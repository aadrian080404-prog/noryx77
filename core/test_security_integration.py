from .defense import DefenseController, SegmentationPolicy, TrustDecision
from .security_integration import DefenseGate, SecurityEnvelope


def envelope(**overrides):
    values = {
        "principal_id": "principal",
        "component_id": "agent",
        "source_zone": "zone-a",
        "target_zone": "zone-a",
        "capability": "observe",
    }
    values.update(overrides)
    return SecurityEnvelope(**values)


def test_same_zone_requests_still_cross_defense_authorization_boundary():
    controller = DefenseController()
    decision = DefenseGate(controller).evaluate(envelope())
    assert decision["allowed"] is True
    assert decision["decision"] == TrustDecision.ALLOW.value
    assert decision["reason"] == "policy_ok"


def test_same_zone_revoked_principal_is_denied():
    controller = DefenseController()
    controller.revoke("principal")
    decision = DefenseGate(controller).evaluate(envelope())
    assert decision["allowed"] is False
    assert decision["decision"] == TrustDecision.DENY.value
    assert decision["reason"] == "principal_revoked"


def test_cross_zone_request_uses_canonical_segmentation_policy():
    policy = SegmentationPolicy()
    policy.allow("agent", "zone-b")
    controller = DefenseController(segmentation=policy)
    decision = DefenseGate(controller).evaluate(envelope(target_zone="zone-b"))
    assert decision["allowed"] is True
    assert decision["decision"] == TrustDecision.ALLOW.value


def test_cross_zone_request_without_policy_is_denied():
    controller = DefenseController()
    decision = DefenseGate(controller).evaluate(envelope(target_zone="zone-b"))
    assert decision["allowed"] is False
    assert decision["decision"] == TrustDecision.DENY.value
    assert decision["reason"] == "segmentation_denied"


def test_invalid_context_fails_closed():
    controller = DefenseController()
    decision = DefenseGate(controller).evaluate(envelope(context={"session_id": 123}))
    assert decision == {"allowed": False, "reason": "invalid_security_context"}
