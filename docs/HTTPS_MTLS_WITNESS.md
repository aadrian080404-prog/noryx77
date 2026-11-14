# HTTPS/mTLS witness transport

`HTTPSWitnessClient` and `make_witness_server` expose the existing signed
SQLite witness state machine over HTTPS. Both sides require TLS 1.2 or newer;
the server requires a client certificate, and the client verifies the server
certificate and hostname against an explicit CA bundle.

The wire schema is strict, request bodies are bounded, non-JSON requests are
rejected, responses are marked no-store, and request bodies/receipt contents
are not logged. The service-side authority still receives its signing key
from outside this module.

Deployment requirements: use a dedicated CA, short-lived client certificates,
certificate rotation/revocation, network ACLs, rate limiting, independent
witness storage/backup, external KMS/HSM for the signing key, and supervised
service lifecycle. mTLS authenticates the TLS peer but does not itself provide
quorum consensus or database anti-rollback.
