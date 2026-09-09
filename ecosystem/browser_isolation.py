"""Static isolation gate for the standalone NORYX Browser front.

The browser is intentionally an AI-free WebView surface. The browser may use
an explicit network Gateway boundary, but it must not contain direct cognitive
runtime, model-provider, chatbot, telemetry or tracking integration.
"""
from __future__ import annotations

from pathlib import Path
import re

FORBIDDEN_MARKERS = (
    "hypersynth",
    "noryx7runtime",
    "chatbot",
    "openai",
    "anthropic",
    "gemini",
    "telemetry",
    "analytics",
    "tracking",
    "addjavascriptinterface",
)

ALLOWED_EXTENSIONS = {".kt", ".kts", ".xml", ".gradle", ".properties", ".json"}
GENERATED_DIRS = {"build", ".gradle", ".idea"}


def _strip_non_code(text: str) -> str:
    """Remove comments and quoted literals before checking direct integrations.

    Endpoint/resource values and explanatory comments are not executable
    integrations. Keeping them out of the marker scan prevents false positives
    while leaving imports, identifiers and API calls visible to the gate.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"'''(?:.|\n)*?'''", "\"\"\"\"\"\"", text)
    text = re.sub(r'"""(?:.|\n)*?"""', '""', text)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
    return text.lower()


def scan_browser_isolation(repository_root: str | Path | None = None) -> tuple[str, ...]:
    root = Path(repository_root).resolve() if repository_root is not None else Path(__file__).resolve().parents[1]
    browser = root / "noryx-browser"
    if not browser.is_dir():
        return ("browser_directory_missing",)

    violations: list[str] = []
    for path in sorted(browser.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        if any(part in GENERATED_DIRS for part in path.relative_to(browser).parts):
            continue
        try:
            text = _strip_non_code(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            violations.append(f"unreadable:{path.relative_to(root)}")
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                violations.append(f"forbidden:{marker}:{path.relative_to(root)}")
    return tuple(violations)


def require_browser_isolation(repository_root: str | Path | None = None) -> None:
    violations = scan_browser_isolation(repository_root)
    if violations:
        raise RuntimeError("browser_isolation_failed:" + ",".join(violations))
