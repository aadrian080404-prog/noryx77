# Runtime Durable Identity Mode

`RuntimeEngine(require_durable_identity_registry=True)` rejects construction unless an identity registry is injected and advertises durable persistence. The high-risk authorization path rechecks that the registry remains available. This strict mode is opt-in; compatibility behavior is unchanged.

Use `core.DurableIdentityRegistry` with an externally provisioned integrity key. Closing the registry makes it unavailable for strict runtime operation.

This does not provide distributed revocation propagation or remote trust-root consensus. The identity registry remains single-host/single-process and needs an external monotonic witness for full snapshot rollback detection.
