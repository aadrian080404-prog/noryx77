"""Global structural gate: one deterministic entry point for freeze verification."""

import importlib

import pytest

from ecosystem.completeness import evaluate, require_complete


REQUIRED_MODULES = (
    "core.actions",
    "core.crypto",
    "core.hypersynth",
    "core.hypersynth_runtime",
    "core.identity",
    "core.metacognition",
    "core.offline",
    "core.recovery",
    "core.runtime",
    "core.state",
    "core.tools",
    "ecosystem.boundaries",
    "ecosystem.dispatch_contract",
    "ecosystem.global_fabric",
    "ecosystem.orchestration",
    "ecosystem.runtime_dispatch",
    "jarvis.core.runtime",
    "jarvis.core.state",
    "jarvis.core.recovery",
)


def test_complete_architecture_gate_is_green():
    complete, problems = evaluate()
    assert complete, problems
    require_complete()


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_canonical_runtime_modules_import_without_shadowing(module_name):
    module = importlib.import_module(module_name)
    assert module.__name__ == module_name


def test_no_competing_core_package_exists():
    module = importlib.import_module("core")
    assert "/core/core" not in module.__file__.replace("\\", "/")
