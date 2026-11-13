# Lifecycle-bound external key provider

`core.LifecycleBoundKeyProvider` connects the durable key lifecycle metadata to the existing cryptographic `KeyProvider` contract. Each key lookup first checks that the metadata store is durable and the requested key is ACTIVE, then asks the injected external KMS/HSM boundary for the exact recorded version.

The adapter does not cache or persist key material. It rejects non-256-bit key responses and becomes unavailable if the lifecycle store is closed.

## Limits

The external KMS/HSM implementation is still supplied by the deployment. This adapter does not provision credentials, implement provider-specific rotation or guarantee atomic coordination between an external KMS and the local metadata journal. A rotation operation must be coordinated with the provider so the requested version exists before it becomes active.