# WAVE 17 — NORYX BROWSER & DEVICE FABRIC

Dependency: Wave 16 CLOSED.

## Goal
Connect NORYX Browser, mobile/device surfaces and future hardware/edge clients to canonical NORYX7 session, identity, authorization and runtime APIs.

## Must verify
- browser is a real client of canonical gateway APIs;
- UI state reflects actual backend capability state;
- scrolling/input behavior is robust on mobile;
- browser cannot obtain hidden privileged APIs;
- session expiration/revocation propagates to the client;
- cleartext/unsafe navigation remains blocked;
- device capabilities are explicitly registered and authorized.

## Closure tests
Browser → session → execute → result, offline transition, session expiry, revoked capability, malformed response, mobile scrolling/input, device capability denial and hosted deployment parity.
