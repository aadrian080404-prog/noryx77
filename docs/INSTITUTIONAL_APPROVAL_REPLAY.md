# Institutional Access — One-Shot Approval Replay Protection

Status: implementation candidate in PR #21; CI pending.

## Implemented

The institutional disclosure gate can now receive an `AuthorizationReplayGuard` and atomically consume the approval quorum after every mandate, scope, role, independence and signature check has succeeded.

- Every approval produces a domain-separated replay token bound to request digest, approver ID, role, issue time and signature digest.
- The full quorum token batch is consumed atomically: either every approval is consumed or none is.
- Reusing the same approval signature for the same request is rejected.
- A file-backed replay guard preserves consumption across process restarts.
- `require_durable_approval_replay=True` rejects missing or in-memory replay storage.
- `require_authenticated_approval_replay=True` additionally requires the HMAC-authenticated replay guard.
- Storage failures fail closed and no disclosure decision is authorized.

The gate remains policy-only: it authorizes a narrowly scoped plan and does not execute queries or release records.

## Configuration

For a high-assurance institutional deployment, provision an authenticated replay guard with a key external to the database, then pass it with `require_authenticated_approval_replay=True`. The guard's key ID must be stable and rotation must be managed through a reviewed migration protocol.

## Limits

- The one-shot tokens are keyed by the exact quorum approvals; this prevents replay of that approval set. It does not implement a broader global revocation service for all previously issued mandates or approver identities.
- HMAC-authenticated replay storage detects row tampering but not deletion or rollback of the complete SQLite database; a production external monotonic witness remains necessary.
- Trust-root provisioning, signature key lifecycle, legal review, query sandboxing and durable disclosure audit are separate deployment requirements.
- Compatibility mode without a replay guard remains available and is not one-shot.
