# NORYX7 Cloud Deployment

## Architecture rule

The cloud provider is infrastructure only. NORYX7 owns the execution protocol, gateway, runtime, identity, authorization, verification, memory and capability routing.

```text
NORYX Browser / API clients
        |
        v
NORYX System Protocol v1
        |
        v
NORYX7 hosted node
        |
        +-- Canonical Gateway
        +-- HYPERSYNTH Runtime
        +-- Agent Fabric
        +-- Resource / Model Routing
        +-- Security / Authorization
        +-- Verification / Metacognition
        +-- Memory / Audit
        +-- External Capability Fabric
```

## Runtime image

The repository `Dockerfile` starts the canonical hosted entrypoint:

`python web/serve.py`

The image is provider-neutral and listens on `PORT` (default `8080`).

## Current transport

The first-party Android Browser uses:

- `POST /v1/browser/session`
- `POST /v1/system/execute`

The second endpoint accepts `NORYX_SYSTEM_PROTOCOL` version `1` envelopes. It delegates to the same cached `NoryxGateway` instance used by the existing `/v1/execute` path. It must never create a second runtime.

## Google Cloud Run

Preferred production topology:

```text
custom NORYX7 domain
        |
        v
Global external Application Load Balancer
        |
        v
Cloud Run NORYX7 service
        |
        v
NORYX7 runtime container
```

Use a managed TLS certificate and route the custom domain to the load balancer. Keep the provider-specific configuration outside the NORYX7 System Protocol.

## Azure Container Apps

The same container image can be deployed to Azure Container Apps. Enable HTTPS ingress and bind the NORYX7 custom domain with a managed certificate. Internal service-to-service calls can remain private inside the Container Apps environment when the architecture is later split into multiple services.

## Required production configuration

At minimum:

- `GROQ_API_KEY` or another explicitly configured model provider
- `NORYX_GATEWAY_BOOTSTRAP_TOKEN`
- `NORYX_GATEWAY_SIGNING_SECRET`
- `NORYX_BROWSER_PAIRING_CODE`
- `NORYX7_MODEL_PROVIDER`
- `NORYX7_MAX_TASK_SECONDS`

External actions remain fail-closed until their provider adapters and authorization material are actually configured.

## Migration rule

Render is not part of the NORYX7 architecture contract. A Render deployment may remain temporarily useful for testing, but replacing it with Cloud Run or Azure must not require changing the Browser protocol or the cognitive runtime.
