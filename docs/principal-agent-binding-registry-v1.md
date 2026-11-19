# Durable principal-agent ownership bindings v1

## Purpose

PrincipalIdentity and AgentIdentity are distinct trust domains. The identity
registries prove that each identifier is currently trusted; they do not prove
that a principal owns or controls a given agent. This module adds that missing
relationship as a separate, durable provisioning record.

## Contract

- A privileged provisioning path calls `bind(principal_id, agent_id)`.
- Both identities must be live in their authoritative SQLite trust registries
  during binding.
- Each agent ID can be assigned to at most one principal. A principal may own
  multiple agents.
- Relationship revocation writes an irreversible tombstone and removes the
  active binding. Rebinding the same pair is denied.
- Every ownership query rechecks both live identity registries and then the
  active relationship. Database or trust-store errors return false.
- Revoking a binding does not revoke either identity. Revoking either identity
  invalidates the relationship at verification time.

## Security boundaries

This is a local durable ownership registry, not authentication, enrollment,
authorization to execute tools, or a multi-host consensus service. The
provisioning caller must already be authorized. Separate SQLite files do not
provide a cross-database atomic transaction; a failed provisioning attempt
may leave no binding, but cannot create a binding without both live trust
checks. A revoked identity is rejected on every subsequent ownership check.

Agent reassignment is intentionally not supported under the same agent ID.
Provision a new AgentIdentity and bind the new ID to the destination principal.
