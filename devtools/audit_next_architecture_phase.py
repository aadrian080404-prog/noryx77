from pathlib import Path
import ast
import json
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = [
    "core",
    "noryx7_runtime",
    "ecosystem",
    "jarvis",
    "tools",
    "tests",
]

def run(cmd):
    try:
        return subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        ).stdout
    except Exception as exc:
        return f"ERROR: {exc}"

modules = []
imports = []
classes = []
functions = []
syntax_errors = []

for dirname in SCAN_DIRS:
    base = ROOT / dirname
    if not base.exists():
        continue

    for path in sorted(base.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        modules.append(rel)

        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
        except Exception as exc:
            syntax_errors.append({
                "file": rel,
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "file": rel,
                        "module": alias.name,
                        "line": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "file": rel,
                    "module": "." * node.level + (node.module or ""),
                    "line": node.lineno,
                })

            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "file": rel,
                    "name": node.name,
                    "line": node.lineno,
                })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "file": rel,
                    "name": node.name,
                    "line": node.lineno,
                })

key_files = [
    "core/hypersynth.py",
    "core/context.py",
    "core/memory.py",
    "core/runtime.py",
    "core/orchestrator.py",
    "core/verification.py",
    "core/recovery.py",
    "core/planning.py",
    "core/reasoning.py",
    "core/simulation.py",
]

key_file_status = {
    item: (ROOT / item).exists()
    for item in key_files
}

git_status = run(["git", "status", "--short"])
git_branch = run(["git", "branch", "--show-current"]).strip()
git_head = run(["git", "rev-parse", "--short", "HEAD"]).strip()
git_log = run(["git", "log", "--oneline", "-8"])

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "root": str(ROOT),
    "python": sys.version,
    "git": {
        "branch": git_branch,
        "head": git_head,
        "status": git_status,
        "recent_commits": git_log,
    },
    "scan": {
        "directories": SCAN_DIRS,
        "python_modules": len(modules),
        "classes": len(classes),
        "functions": len(functions),
        "imports": len(imports),
        "syntax_errors": syntax_errors,
    },
    "key_architecture_files": key_file_status,
    "modules": modules,
    "classes": classes,
}

out = ROOT / "reports" / "architecture_audit.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("NORYX7 ARCHITECTURE AUDIT = COMPLETE")
print(f"BRANCH = {git_branch}")
print(f"HEAD = {git_head}")
print(f"PYTHON MODULES = {len(modules)}")
print(f"CLASSES = {len(classes)}")
print(f"FUNCTIONS = {len(functions)}")
print(f"IMPORTS = {len(imports)}")
print(f"SYNTAX ERRORS = {len(syntax_errors)}")
print()

print("KEY ARCHITECTURE:")
for name, exists in key_file_status.items():
    print(f"{'OK' if exists else 'MISSING'}  {name}")

print()
print(f"REPORT = {out}")

if syntax_errors:
    print()
    print("SYNTAX ERRORS DETECTED:")
    for item in syntax_errors:
        print(f"{item['file']}: {item['error']}")
    raise SystemExit(1)

print()
print("ARCHITECTURE STATIC AUDIT = PASS")
