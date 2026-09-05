"""Static isolation gate for the standalone NORYX Browser front.

The browser is intentionally an AI-free WebView surface. This gate checks only
integration markers that would create a direct dependency on NORYX7/HYPERSYNTH,
agent/chatbot providers, telemetry or tracking. Generic Android APIs are not
forbidden because the browser itself necessarily uses the Android SDK.
"""
from __future__ import annotations

from pathlib import Path

FORBIDDEN_MARKERS = (
    "hypersynth",
    "noryx7",
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


def scan_browser_isolation(repository_root: str | Path | None = None) -> tuple[str, ...]:
    root = Path(repository_root).resolve() if repository_root is not None else Path(__file__).resolve().parents[1]
    browser = root / "noryx-browser"
    if not browser.is_dir():
        return ("browser_directory_missing",)
    violations: list[str] = []
    for path in sorted(browser.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8").lower()
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
