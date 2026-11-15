from gateway.runtime_adapter import RuntimeAdapter


class FakeRuntime:
    pass


def test_runtime_adapter_uses_injected_factory():
    runtime = FakeRuntime()
    calls = []

    def factory():
        calls.append(True)
        return runtime

    adapter = RuntimeAdapter(runtime_factory=factory)

    assert adapter.runtime is runtime
    assert calls == [True]


def test_runtime_adapter_accepts_injected_runtime_without_factory():
    runtime = FakeRuntime()

    adapter = RuntimeAdapter(runtime)

    assert adapter.runtime is runtime


def test_runtime_and_factory_cannot_be_supplied_together():
    import pytest

    with pytest.raises(ValueError, match="runtime_and_factory_are_mutually_exclusive"):
        RuntimeAdapter(FakeRuntime(), runtime_factory=FakeRuntime)


def test_default_runtime_factory_is_the_operational_bootstrap(monkeypatch):
    import noryx7_operational

    runtime = FakeRuntime()
    monkeypatch.setattr(noryx7_operational, "build_runtime", lambda: runtime)

    adapter = RuntimeAdapter()

    assert adapter.runtime is runtime
