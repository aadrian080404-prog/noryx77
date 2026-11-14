from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{path}: expected exactly 1 occurrence, found {count}: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Canonical creator identity
# ---------------------------------------------------------------------------

identity = ROOT / "core" / "agent_identity.py"

replace_once(
    identity,
    'NORYX7_FOUNDER: Final[str] = "Adrian"',
    'NORYX7_FOUNDER: Final[str] = "Adrian Aristodemo"',
)


# ---------------------------------------------------------------------------
# 2. Native LLM agent identity
#
# NORYX7 remains the system/project identity.
# Adrian Aristodemo is the creator/founder/inviter.
# ---------------------------------------------------------------------------

agent = ROOT / "core" / "llm" / "agent.py"

replace_once(
    agent,
    'creator = "NORYX7"',
    'creator = "Adrian Aristodemo"',
)


# ---------------------------------------------------------------------------
# 3. Real Primary -> Secondary allocation inside HYPERSYNTH
#
# Before this change, preferred_agent forced every plan step onto the same
# agent. That made the secondary effectively unreachable from the canonical
# runtime path.
#
# New behavior:
#   - if a preferred agent exists, it handles the first assignment;
#   - subsequent assignments rotate through the other available trusted
#     agents;
#   - with two agents this produces Primary -> Secondary -> Primary...
#   - if only one agent exists, behavior remains unchanged.
# ---------------------------------------------------------------------------

hypersynth = ROOT / "core" / "hypersynth.py"

old = '''        assignments = []
        for index, step in enumerate(plan.steps):
            agent_id = (
                preferred_agent
                if preferred_agent is not None
                else agents[index % len(agents)]
            )
            if preferred_agent is not None and preferred_agent not in agents:
'''

new = '''        assignments = []
        if preferred_agent is not None and preferred_agent not in agents:
            return self._reject(
                "allocation",
                task,
                VerificationResult(
                    False,
                    "allocation",
                    "preferred_agent_unavailable",
                ),
            )

        ordered_agents = list(agents)
        if preferred_agent is not None:
            ordered_agents.remove(preferred_agent)
            ordered_agents.insert(0, preferred_agent)

        for index, step in enumerate(plan.steps):
            agent_id = ordered_agents[index % len(ordered_agents)]
'''

replace_once(hypersynth, old, new)


# ---------------------------------------------------------------------------
# 4. Reproducible architecture marker
# ---------------------------------------------------------------------------

marker = ROOT / "NORYX7_CONTEXT" / "ARCHITECTURE_STATUS.md"
if marker.exists():
    text = marker.read_text(encoding="utf-8")
    section = """

### Frontier native agent mesh

- System identity: `NORYX7`
- Creator/founder/inviter: `Adrian Aristodemo`
- Primary agent: `noryx7-llm`
- Secondary agent: `noryx7-secondary`
- Agent execution remains behind authorization, ActionGate, Supervisor and verification.
- HYPERSYNTH allocation rotates across trusted available agents instead of pinning
  every step to the preferred agent.
"""
    if "### Frontier native agent mesh" not in text:
        marker.write_text(text.rstrip() + section + "\n", encoding="utf-8")


print("NORYX7 FRONTIER AGENT MESH PATCHED")
print("creator = Adrian Aristodemo")
print("system identity = NORYX7")
print("primary = noryx7-llm")
print("secondary = noryx7-secondary")
print("hypersynth allocation = trusted multi-agent rotation")
