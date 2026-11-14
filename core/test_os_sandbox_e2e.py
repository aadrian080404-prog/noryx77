"""Opt-in Linux integration test for the real Bubblewrap boundary.

Run with NORYX7_RUN_BWRAP_E2E=1 on a host that permits unprivileged user
namespaces. This is intentionally not replaced by a fake adapter test.
"""
import os
import sys

import pytest

from core.os_sandbox import BubblewrapSandboxRunner, SandboxLimits


@pytest.mark.skipif(
    os.environ.get("NORYX7_RUN_BWRAP_E2E") != "1",
    reason="set NORYX7_RUN_BWRAP_E2E=1 to exercise real Bubblewrap namespaces",
)
@pytest.mark.skipif(sys.platform != "linux", reason="Bubblewrap requires Linux")
def test_bubblewrap_executes_in_workspace_without_network(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = BubblewrapSandboxRunner()
    program = (
        "from pathlib import Path\n"
        "import socket\n"
        "Path('/workspace/noryx7-e2e-marker').write_text('sandbox-ok')\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=1)\n"
        "except OSError:\n"
        "    print('network-denied')\n"
        "else:\n"
        "    raise SystemExit('sandbox-network-not-isolated')\n"
    )
    result = runner.run(
        ("/usr/bin/python3", "-I", "-c", program),
        workspace=workspace,
        limits=SandboxLimits(wall_seconds=10, output_bytes=4096),
    )
    assert not result.timed_out
    assert result.exit_code == 0, result.stderr.decode("utf-8", "replace")
    assert result.stdout.strip() == b"network-denied"
    assert (workspace / "noryx7-e2e-marker").read_text() == "sandbox-ok"
