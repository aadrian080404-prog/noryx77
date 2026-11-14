# AgentFabric identity authorization linearization

AgentFabric now obtains its principal-authorization decision through
`IdentityRegistry.with_trusted_identity`. For the in-memory and SQLite
registries, this serializes the short identity comparison and principal policy
callback against concurrent revocation.

The authorization callback is deliberately limited to decision-making. Agent
code is invoked only after the registry critical section has completed.
A dispatch whose authorization decision linearized before revocation is
considered in flight and may finish; revocation prevents later dispatch
authorizations. This avoids executing arbitrary agent code while holding a
database write transaction.

This does not cancel already-running agent tasks or provide distributed
revocation across independent hosts. Cross-node revocation still requires
authenticated replication and an agreed trust/consensus authority.
