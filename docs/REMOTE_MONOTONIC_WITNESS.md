# Remote Monotonic Witness and Anchored State Journal

`core.RemoteMonotonicAnchor` adapts an externally operated witness client to the existing monotonic-anchor contract. It verifies Ed25519 signatures over canonical receipts bound to a fresh 32-byte request nonce, witness identity, operation and returned sequence/MAC snapshot. The transport/client is injected; credentials and private signing keys remain outside NORYX7.

`core.AnchoredStateJournal` coordinates the SQLite state journal with that external anchor:
- verifies the local authenticated journal head against the external head before reads and appends;
- advances the witness with compare-and-swap after each durable local commit;
- detects a rolled-back SQLite snapshot when the external head is newer;
- reconciles exactly one valid local record ahead of the witness, representing the known crash window after DB commit and before witness CAS;
- rejects larger or mismatched divergence.

## Production requirements and limits

The remote service must implement durable monotonic compare-and-swap, authenticate clients, protect its own state against rollback, and sign nonce-bound receipts with a key whose public key is pinned by the client. A fake/in-memory anchor is test-only and does not provide rollback resistance. This PR supplies the client adapter contract and journal integration, not a hosted witness service, cloud credentials, mTLS provisioning, high availability or operational key rotation. Availability of the witness is required for anchored reads/appends; failures are fail-closed.
