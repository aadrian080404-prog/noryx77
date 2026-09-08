# NORYX7 source protection boundary

NORYX7 source code is proprietary implementation material. The repository is currently configured as **private**; this is the first access-control boundary.

## Required production model

1. Keep the source repository private and grant repository access only to explicitly trusted maintainers.
2. Keep credentials, private keys, signing material, model/provider secrets and deployment secrets out of Git. Store them in a managed secret/KMS system.
3. Do not ship Python/Kotlin source, repository history, debug symbols, test fixtures containing secrets, or development credentials to end-user devices.
4. Deploy sensitive NORYX7 execution components server-side from the private repository. Clients and NORYX Browser receive only the minimum signed runtime artifacts/API surface required for operation.
5. Protect release artifacts with signing and verify signatures before deployment or execution.
6. Require owner review for source changes. `CODEOWNERS` records the repository owner as the required code owner; GitHub branch/ruleset enforcement must be enabled on the repository before treating this as a hard merge block.
7. Keep production and development credentials separate and rotate credentials after any suspected exposure.
8. Log access and release events without logging source, credentials, private keys or sensitive user data.

## What this can and cannot guarantee

A private repository prevents public browsing but cannot make source code mathematically impossible for every authorized administrator or a compromised build/deployment environment to view or steal. Software that executes on a user's device can also be inspected by a sufficiently privileged owner of that device.

Therefore, the strongest practical design is **source stays server-side; clients receive signed, least-privilege artifacts and never receive the proprietary source**. Hardware-backed keys, isolated build/deploy infrastructure, strict repository access, and verified releases are required for the strongest protection.

This document is a security boundary, not a claim that source secrecy is absolute.
