"""Build a reproducible, conservative repository component/dependency inventory.

This is static inventory, not proof of runtime integration or security verification.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

SOURCE_SUFFIXES = {".py", ".kt", ".kts", ".rs", ".go", ".ts", ".tsx", ".js", ".java"}
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "build", "dist"}

DOMAINS: dict[str, dict[str, list[str]]] = {
    "A_foundation_contracts": {"roots": ["core/contracts.py", "jarvis/core/contracts.py", "noryx7_runtime/contracts.py", "ecosystem/"], "tokens": ["contract", "schema", "proof", "attestation"]},
    "B_identity_authorization": {"roots": ["core/identity.py", "core/agent_identity.py", "core/actions.py", "core/authorization", "core/multiauth.py", "core/key_lifecycle.py", "jarvis/security/", "noryx7_runtime/capabilities.py"], "tokens": ["identity", "authorization", "principal", "capability", "trust_chain"]},
    "C_cryptography_privacy": {"roots": ["core/crypto.py", "core/secure_", "core/perimeter.py", "core/egress.py", "core/offline_anchor.py"], "tokens": ["crypto", "secure", "privacy", "key_", "egress", "anchor"]},
    "D_state_persistence": {"roots": ["core/state", "core/journal", "noryx7_runtime/state.py", "noryx7_runtime/recovery.py", "jarvis/core/state.py"], "tokens": ["journal", "persistence", "recovery", "state_commit"]},
    "E_memory_fabric": {"roots": ["core/memory", "core/secure_memory.py", "jarvis/memory/"], "tokens": ["memory", "fabric_memory"]},
    "F_cognition_hypersynth": {"roots": ["core/hypersynth", "core/reasoning.py", "core/decomposition.py", "core/finch.py", "core/universal_intelligence.py"], "tokens": ["cognitive", "hypersynth", "reasoning", "personality", "user_understanding"]},
    "G_planning_execution": {"roots": ["core/planning.py", "core/orchestration.py", "core/execution", "core/agent_runtime.py", "noryx7_runtime/engine.py", "noryx7_runtime/scheduler.py", "jarvis/core/orchestrator.py"], "tokens": ["planning", "task_graph", "orchestration", "execution", "scheduler", "dispatch"]},
    "H_metacognition_learning": {"roots": ["core/metacognition.py", "core/metacognitive_challenge.py", "core/self_improvement.py", "core/evaluation"], "tokens": ["metacogn", "self_improvement", "evaluation"]},
    "I_runtime_assurance": {"roots": ["core/runtime.py", "core/operational_runtime.py", "core/sandbox.py", "core/supervisor.py", "noryx7_runtime/", "ecosystem/runtime"], "tokens": ["runtime", "sandbox", "supervisor", "isolation", "lifecycle"]},
    "J_adversarial_defense": {"roots": ["core/adversarial", "core/defense.py", "core/cyber_range.py", "core/scenario_matrix.py", "tests/million"], "tokens": ["adversarial", "defense", "cyber_range", "scenario", "campaign", "attack"]},
    "K_surf_reverse_engineering": {"roots": ["core/surf_", "docs/SURF_"], "tokens": ["surf", "reverse", "dependency", "architecture_audit"]},
    "L_deception_moving_target": {"roots": ["core/deception", "core/decoy"], "tokens": ["deception", "decoy", "honey", "moving_target"]},
    "M_osint_intelligence": {"roots": ["core/osint"], "tokens": ["osint", "intelligence_source"]},
    "N_communications_distributed": {"roots": ["core/distributed.py", "core/secure_channel.py", "core/device_fabric.py", "core/agent_mesh.py", "core/secure_data_plane.py", "services/"], "tokens": ["distributed", "mesh", "transport", "channel", "network", "edge"]},
    "O_financial_institutional": {"roots": ["core/institutional_access.py", "core/payment", "core/finance"], "tokens": ["payment", "financial", "ledger", "institutional", "marketplace"]},
    "P_device_hardware_energy": {"roots": ["core/device", "core/secure_boot.py", "android/", "noryx-browser/", "ios/"], "tokens": ["device", "hardware", "secure_boot", "energy", "browser"]},
    "Q_governance_operations": {"roots": ["gateway/", "docs/", "architecture/", ".github/workflows/", "SECURITY.md", "CODEOWNERS"], "tokens": ["governance", "audit", "operations", "policy", "incident"]},
}


def _domain_matches(path: str, spec: dict[str, list[str]]) -> bool:
    lower = path.lower()
    return any(path.startswith(root) for root in spec["roots"]) or any(token in lower for token in spec["tokens"])


def _python_metadata(path: Path, root: Path, module_names: set[str]) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=path.as_posix())
    except (OSError, UnicodeError, SyntaxError) as exc:
        return {"parse_status": "error", "parse_error": type(exc).__name__, "imports": [], "symbols": []}
    imports: set[str] = set()
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    internal = sorted(name for name in imports if name in module_names or any(m.startswith(name + ".") for m in module_names))
    return {"parse_status": "ok", "imports": sorted(imports), "internal_imports": internal, "symbols": sorted(set(symbols))}


def build_inventory(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    files = sorted(
        p for p in root.rglob("*")
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts)
    )
    relative = [p.relative_to(root).as_posix() for p in files]
    py_modules = set()
    for name in relative:
        if name.endswith(".py"):
            module = name[:-3].replace("/", ".")
            if module.endswith(".__init__"):
                module = module[:-9]
            py_modules.add(module)

    records = []
    for path, name in zip(files, relative):
        domains = [domain for domain, spec in DOMAINS.items() if _domain_matches(name, spec)]
        record: dict[str, Any] = {
            "path": name,
            "kind": "test" if "test" in path.name.lower() else "source" if path.suffix in SOURCE_SUFFIXES else "documentation_or_config",
            "domains": domains,
            "lifecycle": "source_present_not_proof_of_integration",
            "test_candidates": [],
        }
        if path.suffix == ".py":
            record.update(_python_metadata(path, root, py_modules))
        stem = path.stem.lower().replace("test_", "").replace("_test", "")
        if record["kind"] == "source":
            record["test_candidates"] = [
                candidate for candidate in relative
                if ("test" in Path(candidate).name.lower())
                and (stem in Path(candidate).stem.lower() or Path(candidate).stem.lower().replace("test_", "") in stem)
            ]
        records.append(record)

    dependency_edges = []
    for record in records:
        for imported in record.get("internal_imports", []):
            dependency_edges.append({"source": record["path"], "imports": imported})

    canonical_registry_path = root / "architecture" / "component_registry.json"
    canonical_registry = None
    if canonical_registry_path.is_file():
        canonical_registry = json.loads(canonical_registry_path.read_text(encoding="utf-8"))
        if canonical_registry.get("schema_version") != 1 or not isinstance(canonical_registry.get("domains"), list):
            raise ValueError("canonical_component_registry_schema_invalid")
        domain_ids = {item.get("id") for item in canonical_registry["domains"] if isinstance(item, dict)}
        allowed_states = set(canonical_registry.get("domain_status_vocabulary", []))
        if (
            len(domain_ids) != 17
            or any(not set(item.get("depends_on", [])) <= domain_ids for item in canonical_registry["domains"])
            or any(item.get("current_state") not in allowed_states for item in canonical_registry["domains"])
        ):
            raise ValueError("canonical_component_registry_domains_invalid")

    return {
        "schema_version": 1,
        "inventory_scope": "repository_files_static_imports_and_ast_symbols",
        "verification_warning": "File presence and test-name candidates do not prove runtime call-path integration, test execution, independent verification or production qualification.",
        "analysis_limits": {
            "dynamic_imports": "not_resolved",
            "function_call_graph": "not_built",
            "runtime_call_paths": "not_proven",
            "test_execution_evidence": "must_be_joined_from_exact_commit_CI_artifacts",
            "vulnerability_status": "not_assessed_by_inventory",
        },
        "domain_catalog": canonical_registry["domains"] if canonical_registry else list(DOMAINS),
        "canonical_registry_source": "architecture/component_registry.json" if canonical_registry else None,
        "file_count": len(records),
        "source_file_count": sum(item["kind"] == "source" for item in records),
        "python_file_count": sum(item["path"].endswith(".py") for item in records),
        "dependency_edge_count": len(dependency_edges),
        "files": records,
        "static_import_edges": dependency_edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="architecture/component_registry.generated.json")
    args = parser.parse_args()
    result = build_inventory(args.root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("file_count", "source_file_count", "python_file_count", "dependency_edge_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
