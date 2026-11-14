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
        "import json, resource, socket\n"
        "limits = {name: resource.getrlimit(kind)[0] for name, kind in {"
        "'cpu': resource.RLIMIT_CPU, 'as': resource.RLIMIT_AS, "
        "'fsize': resource.RLIMIT_FSIZE, 'nofile': resource.RLIMIT_NOFILE, "
        "'nproc': resource.RLIMIT_NPROC, 'core': resource.RLIMIT_CORE}.items()}\n"
        "Path('/workspace/noryx7-e2e-marker').write_text('sandbox-ok')\n"
        "Path('/workspace/noryx7-e2e-limits.json').write_text(json.dumps(limits))\n"
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
        limits=SandboxLimits(
            cpu_seconds=3,
            memory_bytes=64 * 1024 * 1024,
            file_size_bytes=1234,
            open_files=20,
            processes=5,
            wall_seconds=10,
            output_bytes=4096,
        ),
    )
    assert not result.timed_out
    assert result.exit_code == 0, result.stderr.decode("utf-8", "replace")
    assert result.stdout.strip() == b"network-denied"
    assert (workspace / "noryx7-e2e-marker").read_text() == "sandbox-ok"
    import json
    observed = json.loads((workspace / "noryx7-e2e-limits.json").read_text())
    assert observed == {
        "cpu": 3,
        "as": 64 * 1024 * 1024,
        "fsize": 1234,
        "nofile": 20,
        "nproc": 5,
        "core": 0,
    }

def test_bubblewrap_command_sets_limits_without_preexec_hooks(tmp_path):
    runner = object.__new__(BubblewrapSandboxRunner)
    runner._prlimit = "/usr/bin/prlimit"
    runner._setpriv = "/usr/bin/setpriv"
    runner._bwrap = "/usr/bin/bwrap"
    limits = SandboxLimits(
        cpu_seconds=3,
        memory_bytes=64 * 1024 * 1024,
        file_size_bytes=1234,
        open_files=20,
        processes=5,
    )

    command = runner._command(("/usr/bin/true",), str(tmp_path), limits)

    assert command[:10] == [
        "/usr/bin/prlimit",
        "--cpu=3:4",
        "--as=67108864:67108864",
        "--fsize=1234:1234",
        "--nofile=20:20",
        "--core=0:0",
        "--nproc=5:5",
        "--",
        "/usr/bin/setpriv",
        "--no-new-privs",
    ]
    assert command[10] == "--"
    assert command[11] == "/usr/bin/bwrap"
