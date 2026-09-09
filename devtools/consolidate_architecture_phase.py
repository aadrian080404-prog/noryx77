from pathlib import Path
import json
import ast

ROOT = Path(__file__).resolve().parents[1]

SEARCH_ROOTS = [
    ROOT / "core",
    ROOT / "noryx7_runtime",
    ROOT / "ecosystem",
    ROOT / "jarvis",
    ROOT / "tools",
]

EXPECTED = {
    "hypersynth": [
        "core/hypersynth.py",
    ],
    "context": [
        "core/context.py",
    ],
    "memory": [
        "core/memory.py",
    ],
    "runtime": [
        "core/runtime.py",
    ],
    "verification": [
        "core/verification.py",
    ],
    "recovery": [
        "core/recovery.py",
    ],
    "planning": [
        "core/planning.py",
    ],
    "reasoning": [
        "core/reasoning.py",
    ],
    "orchestration": [
        "core/orchestrator.py",
    ],
    "simulation": [
        "core/simulation.py",
    ],
}

KEYWORDS = {
    "orchestration": (
        "orchestrator",
        "orchestration",
        "execution_loop",
        "process",
        "workflow",
        "dispatch",
    ),
    "simulation": (
        "simulation",
        "simulator",
        "simulate",
    ),
}


def python_files():
    files = []
    for base in SEARCH_ROOTS:
        if base.exists():
            files.extend(base.rglob("*.py"))
    return sorted(set(files))


def inspect_file(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "classes": [],
            "functions": [],
            "imports": [],
        }

    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

    return {
        "classes": sorted(set(classes)),
        "functions": sorted(set(functions)),
        "imports": sorted(set(imports)),
    }


files = python_files()
catalog = {}

for path in files:
    rel = str(path.relative_to(ROOT))
    catalog[rel] = inspect_file(path)

resolved = {}

for capability, expected_paths in EXPECTED.items():
    direct = [p for p in expected_paths if (ROOT / p).exists()]

    matches = []

    if direct:
        matches.extend(direct)

    keywords = KEYWORDS.get(capability, ())

    if keywords:
        for rel, info in catalog.items():
            haystack = " ".join(
                [
                    rel.lower(),
                    *[x.lower() for x in info["classes"]],
                    *[x.lower() for x in info["functions"]],
                ]
            )

            if any(keyword in haystack for keyword in keywords):
                if rel not in matches:
                    matches.append(rel)

    resolved[capability] = {
        "expected": expected_paths,
        "direct": direct,
        "resolved": sorted(matches),
        "status": "resolved" if matches else "missing",
    }

report = {
    "root": str(ROOT),
    "python_files": len(files),
    "capabilities": resolved,
}

report_path = ROOT / "reports" / "architecture_consolidation.json"
report_path.write_text(
    json.dumps(report, indent=2, sort_keys=True),
    encoding="utf-8",
)

print("========================================")
print("NORYX7 ARCHITECTURE CONSOLIDATION")
print("========================================")

for capability, data in resolved.items():
    print()
    print(f"[{capability.upper()}]")
    print("STATUS =", data["status"].upper())

    for item in data["resolved"]:
        print("RESOLVED =", item)

print()
print("REPORT =", report_path)
print("========================================")

unresolved = [
    name
    for name, data in resolved.items()
    if data["status"] == "missing"
]

if unresolved:
    print("UNRESOLVED CAPABILITIES =", ", ".join(unresolved))
else:
    print("ALL ARCHITECTURE CAPABILITIES = RESOLVED")
