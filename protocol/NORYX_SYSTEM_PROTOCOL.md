# NORYX System Protocol

**Status:** v1 draft, canonical architecture contract  
**System:** NORYX7  
**Purpose:** define the transport-neutral contract between first-party clients (including NORYX Browser) and the unified NORYX7 execution fabric.

## 1. Architectural rule

NORYX7 clients MUST NOT implement a second cognitive execution path. A client sends a system request to the NORYX7 execution fabric; the server/runtime owns perception, contracts, planning, routing, authorization, execution, verification, memory and audit.

Cloud infrastructure is a deployment substrate, not the NORYX7 architecture. The protocol MUST remain usable over a local/device transport, a private network, or a hosted HTTPS endpoint without changing the logical execution contract.

## 2. Canonical request envelope

```json
{
  "protocol": "noryx.system",
  "version": "1.0",
  "message_type": "execute",
  "request_id": "<unique-request-id>",
  "execution_id": "<canonical-execution-id>",
  "session_id": "<session-id>",
  "principal_id": "<authenticated-principal>",
  "client_id": "<first-party-client-id>",
  "source": "noryx-browser",
  "input": {
    "text": "..."
  }
}
```

### Required identity fields

- `request_id`: identifies the protocol message.
- `execution_id`: identifies the complete NORYX7 execution lifecycle.
- `session_id`: binds the request to the authenticated session.
- `principal_id`: binds execution authority to the authenticated principal.
- `client_id`: identifies the client instance/application.

A client MUST NOT create independent child execution identities for runtime stages. Internal components derive their stage records from the canonical `execution_id`.

## 3. Response envelope

```json
{
  "protocol": "noryx.system",
  "version": "1.0",
  "message_type": "execute_result",
  "request_id": "<request-id>",
  "execution_id": "<same-execution-id>",
  "status": "completed",
  "result": "...",
  "verification": {
    "valid": true,
    "stage": "output"
  },
  "provenance": {
    "system_id": "NORYX7",
    "runtime": "..."
  }
}
```

`execution_id` in the response MUST equal the request execution identity. A response claiming a different execution identity is invalid.

## 4. Execution lifecycle

The canonical lifecycle is:

`INPUT → PERCEPTION → CONTRACT → CONTEXT → DECOMPOSITION → PLANNING → PLAN VERIFICATION → HYPOTHESIS → SIMULATION → RESOURCE ALLOCATION → ACTION GATE → AGENT EXECUTION → RESULT ADMISSION → RESULT VERIFICATION → CROSS-CHECK → OUTPUT VERIFICATION → METACOGNITION → MEMORY/AUDIT`

Not every task activates every optional capability. The unified runtime decides which stages are required. A required stage MUST NOT be silently bypassed.

## 5. Transport neutrality

The protocol does not require a particular deployment provider.

Supported architectural transports:

- local/device runtime transport;
- private network transport;
- hosted HTTPS transport;
- future distributed NORYX7 node transport.

Google Cloud, Microsoft Azure, Render, or another provider MAY host a NORYX7 node. None is part of the logical system contract.

## 6. External actions

Flights, payments, contracts, bureaucracy, insurance and similar capabilities are executed only through the NORYX7 capability/security fabric. The client MUST NOT call external providers directly as a shortcut around authorization, policy, provenance or verification.

If a required external provider or credential is unavailable, the runtime MUST fail closed and return a truthful unavailable/rejected state.

## 7. First-party browser rule

NORYX Browser is a first-party NORYX7 client. WebView is a web-content component; it is not the NORYX7 cognitive runtime and MUST NOT become a parallel orchestration layer.

The browser's native system bridge SHOULD eventually support both:

1. local/device NORYX7 execution;
2. remote NORYX7 execution through the same protocol.

Switching transport MUST NOT change the semantic execution contract.

## 8. Security requirements

Implementations MUST preserve:

- deny-by-default authorization;
- principal binding;
- replay protection;
- provenance;
- result verification;
- fail-closed behavior for high-risk actions;
- canonical execution identity;
- auditable lifecycle records.

The protocol itself MUST NOT be used to bypass an existing authorization or security boundary.

## 9. Compatibility

Protocol changes MUST be versioned. Unknown required fields, unsupported protocol versions, invalid execution identities, or malformed envelopes MUST be rejected rather than guessed.
