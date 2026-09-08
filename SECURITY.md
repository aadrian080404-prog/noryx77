# NORYX7 Source Security

NORYX7 source code is proprietary and must not be treated as public source.

## Repository boundary

The canonical repository must remain private. Source access is restricted to explicitly authorized maintainers. Runtime users receive deployed artifacts/services, not repository read access.

## Immutability boundary

Production source is not modified directly. Changes flow through reviewed pull requests, automated verification, protected release commits and an audited deployment pipeline. The deployment identity is separate from runtime identities.

GitHub repository administrators must enable branch protection/rulesets outside this repository file with:

- required pull-request review;
- required successful status checks;
- no direct pushes to protected production branches;
- restricted branch deletion/force-push;
- least-privilege repository roles;
- mandatory two-factor authentication for maintainers;
- secret scanning and push protection where available.

## Confidentiality

Source confidentiality cannot be guaranteed by application code alone. Git hosting permissions, developer workstations, CI logs, artifacts and credentials are part of the trust boundary. Never place private keys, tokens, passwords or production secrets in source control.

Production deployments should expose only the minimum runtime interface and should use external secret/key management. Build artifacts should not contain source maps, debug bundles or repository credentials unless explicitly required.

## Recovery

A compromised repository or deployment must be treated as a security incident: revoke affected credentials, rotate signing/deployment keys, invalidate compromised artifacts and restore from a verified trusted revision.

## Important limitation

No software architecture can make source code simultaneously executable on a user's machine and mathematically impossible for that machine's owner or administrator to inspect. For maximum confidentiality, keep source on the private build side and distribute only controlled artifacts or remote services.
