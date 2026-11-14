# Collaboration identity revalidation

When the canonical HYPERSYNTH runtime has an identity registry, the
Primary → Secondary → Primary collaboration protocol now checks that each
agent's registered AgentIdentity is trusted immediately before and after
each inference call. It also checks that the returned AgentResult.agent_id
matches the invoked agent.

The registry lock is deliberately NOT held while model/agent code runs:
inference may be slow or call external providers, and holding the trust lock
would block revocation. Instead, if an identity is revoked or replaced while
the agent is running, the result is discarded before it can influence the
next collaboration stage.

This is a result-integrity boundary, not an execution authorization grant.
All external actions must still pass through ToolExecutor and ActionGate.
Standalone AgentCollaboration instances without an identity registry retain
their compatibility behavior; the canonical runtime supplies its registry.
