# SURF Trusted Verification Receipts

Status: implementation candidate in PR #17; CI not yet verified.

## Implemented

SURF now has an optional strict trust mode. The caller supplies both:
- a receipt provider returning a cryptographically signed `AgentAttestation`;
- an `IdentityRegistry` containing the independently trusted verifier public keys.

SURF constructs a canonical, domain-separated statement for each verification decision. The statement binds:
- receipt type (evidence, hypothesis, candidate, regression, authorization or sandbox);
- a digest of the exact subject;
- a digest of the relevant graph, verified-evidence set or experiment context.

The provider's attestation must contain that exact statement and pass Ed25519 verification against the trusted identity registry. In strict mode, legacy boolean callbacks are ignored for trust decisions. An arbitrary callback returning `True` cannot create a trusted receipt.

`SURFAssessment.verification_trust_level` distinguishes:
- `trusted_identity_signed_receipts`
- `callback_claims_only` (legacy compatibility mode)

## Trust boundary

The identity registry is a trust root and must be provisioned separately from the agent or SURF provider being assessed. The receipt provider can be a local verifier or a separately operated service, but its signing key must remain protected. Revocation must be applied to the registry used by the running service.

## Explicit limitations

- This does not implement live target observation adapters or a sandbox.
- It does not independently prove that the evidence source was lawful, complete or truthful; it authenticates who signed a particular evidence/verification statement.
- Trust-root provisioning, persistence, key rotation, revocation distribution and audit retention remain deployment responsibilities.
- Legacy callback mode remains available for compatibility and is explicitly labelled as callback claims only.
- This is not a complete reverse-engineering engine or a production security certification.
