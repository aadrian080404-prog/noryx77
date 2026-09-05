from core.personality import PersonalityProfile
from core.personality_binding import bind_personality, verify_personality_binding


def profile(agent_id="agent-a", seed=7):
    return PersonalityProfile(agent_id=agent_id, seed=seed, graph_depth=4, node_budget=64)


def test_binding_is_deterministic_for_same_context():
    key = b"k" * 32
    p = profile()
    assert bind_personality(p, agent_id="agent-a", epoch=3, key=key) == bind_personality(
        p, agent_id="agent-a", epoch=3, key=key
    )


def test_binding_changes_when_agent_or_epoch_changes():
    key = b"k" * 32
    p = profile()
    binding = bind_personality(p, agent_id="agent-a", epoch=3, key=key)
    assert not verify_personality_binding(p, agent_id="agent-b", epoch=3, binding=binding, key=key)
    assert not verify_personality_binding(p, agent_id="agent-a", epoch=4, binding=binding, key=key)


def test_binding_changes_when_personality_changes():
    key = b"k" * 32
    binding = bind_personality(profile(seed=7), agent_id="agent-a", epoch=3, key=key)
    assert not verify_personality_binding(profile(seed=8), agent_id="agent-a", epoch=3, binding=binding, key=key)


def test_wrong_key_and_tampering_fail_closed():
    p = profile()
    binding = bind_personality(p, agent_id="agent-a", epoch=3, key=b"k" * 32)
    assert not verify_personality_binding(p, agent_id="agent-a", epoch=3, binding=binding, key=b"x" * 32)
    assert not verify_personality_binding(p, agent_id="agent-a", epoch=3, binding="0" * 64, key=b"k" * 32)


def test_profile_agent_mismatch_is_rejected():
    try:
        bind_personality(profile(agent_id="other"), agent_id="agent-a", epoch=0, key=b"k" * 32)
    except ValueError as exc:
        assert str(exc) == "agent_identity_mismatch"
    else:
        raise AssertionError("expected identity mismatch")
