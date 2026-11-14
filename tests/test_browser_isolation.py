from pathlib import Path

from ecosystem.browser_isolation import scan_browser_isolation


def test_browser_isolation_has_no_forbidden_integration_markers():
    root = Path(__file__).resolve().parents[1]
    assert scan_browser_isolation(root) == ()
