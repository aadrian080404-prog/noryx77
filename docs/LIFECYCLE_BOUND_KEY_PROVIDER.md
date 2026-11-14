# Lifecycle-bound external key provider

`LifecycleBoundKeyProvider` adapts the versioned external KMS/HSM contract to
NORYX7's `KeyProvider.get_key(key_id)` interface. It checks the durable
lifecycle state, requests the exact active key version from the external
provider, validates AES-256 key length, and checks that lifecycle state did not
change during retrieval.

Raw key material remains external; SQLite stores only key ID, version and
state. Retiring/revoked keys are denied. A rotation or revocation observed
during KMS retrieval invalidates the returned bytes.

The final check is the acquisition linearization point: a revocation after it
does not retroactively cancel an operation already holding the key. Callers
must keep key use bounded and avoid caching returned bytes. This adapter does
not replace KMS/HSM access controls, memory zeroization, independent database
anti-rollback, or cryptographic key destruction.
