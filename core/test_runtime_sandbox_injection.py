from core.runtime import NORYXRuntime


class StubSandboxAdapter:
    environment = "sandboxed_process"

    def execute(self, action):
        return {"status": "executed"}


def test_canonical_runtime_exposes_explicit_sandbox_adapter():
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(sandboxed_process_adapter=adapter)

    assert runtime.hypersynth.sandboxed_process_adapter is adapter
    assert runtime.capability_registry.resolve("sandboxed_process") is not None
    assert runtime.capability_registry.risk("sandboxed_process") == "high"


def test_canonical_runtime_keeps_process_capability_disabled_by_default():
    runtime = NORYXRuntime()
    assert runtime.capability_registry.resolve("sandboxed_process") is None


def test_canonical_runtime_binds_collaboration_to_identity_registry():
    runtime = NORYXRuntime()
    assert runtime.hypersynth.collaboration.identity_registry is runtime.identity_registry
