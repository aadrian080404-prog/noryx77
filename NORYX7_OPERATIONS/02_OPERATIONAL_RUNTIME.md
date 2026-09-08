# NORYX7 Operational Runtime

The operational runtime is the executable composition of the canonical NORYX7 graph.

## Runtime graph

`TaskSpec -> NORYXRuntime -> HypersynthRuntime -> HYPERSYNTH -> Planner -> AgentSupervisor -> ToolExecutor -> ActionGate -> capability -> Verification -> Memory/State/Audit`

For ordinary model tasks when a model fabric is configured, the planner selects `agent_collaboration` and the capability executes:

`Primary -> Secondary critique -> Primary reconciliation -> verification`

The collaboration capability is itself dispatched by the canonical `ToolExecutor`, so it does not create a parallel authority path.

## Online agents

`OperationalNORYXRuntime` starts the hosted agent lifecycle after the runtime has created and cryptographically trusted both model agents.

- `noryx7-llm`: Primary
- `noryx7-secondary`: Secondary

`ONLINE` means registered, identity-trusted and routable by the current process. It does not mean that an external model provider is available without credentials.

## Real provider entrypoint

`noryx7_operational.py` uses the existing OpenRouter adapter and requires `OPENROUTER_API_KEY`. It never substitutes a fake provider and fails closed when the key is absent.

## Verification

The operational acceptance tests verify:

- both agents are online;
- Primary/Secondary identities are distinct and trusted;
- ordinary model tasks use the collaboration capability;
- the collaboration result is verified;
- the same execution identity survives the full handshake;
- the completion is visible in runtime audit state.
