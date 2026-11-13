# Runtime identity check scope

RuntimeEngine resolves the adapter's trusted identity under the registry lock, compares its public key to the configured attestation signer, and releases the lock before invoking external adapter code. This prevents a blocked or long-running executor from holding the identity registry lock and delaying revocation indefinitely.

The trust check is the dispatch authorization linearization point: a revocation committed after that check prevents subsequent dispatches but does not retroactively cancel an already-authorized in-flight side effect. High-risk actions still require the separate one-shot multi-approval/replay controls. This behavior is explicit and tested; it is not an instantaneous cancellation guarantee for actions already in progress.
