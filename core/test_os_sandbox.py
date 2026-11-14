import subprocess

import pytest

from core.os_sandbox import BubblewrapSandboxRunner, SandboxLimits


def runner():
    # /bin/true is only used as a validated executable path; Popen is mocked.
    return BubblewrapSandboxRunner(bwrap_path="/bin/true")


def test_limits_reject_booleans_and_out_of_range_values():
    with pytest.raises(ValueError, match="invalid_sandbox_limit"):
        SandboxLimits(cpu_seconds=True)
    with pytest.raises(ValueError, match="invalid_sandbox_limit"):
        SandboxLimits(memory_bytes=1)


def test_runner_fails_closed_without_bubblewrap(monkeypatch):
    monkeypatch.setattr("core.os_sandbox.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="bubblewrap_not_available"):
        BubblewrapSandboxRunner()


def test_argv_requires_absolute_executable():
    with pytest.raises(ValueError, match="absolute"):
        runner()._validate_argv(("python", "-c", "pass"))
    with pytest.raises(ValueError, match="invalid_sandbox_argument"):
        runner()._validate_argv(("/usr/bin/python3", "bad\x00arg"))


def test_workspace_must_exist_and_not_be_symlink(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        runner()._workspace_path(missing)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        runner()._workspace_path(link)


def test_command_disables_network_and_mounts_only_workspace(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    command = runner()._command(("/usr/bin/python3", "-V"), str(work))
    assert "--unshare-net" in command
    assert "--unshare-pid" in command
    assert "--clearenv" in command
    assert "--bind" in command
    assert str(work) in command
    assert "--" in command
    assert command[-1] == "-V"


def test_run_uses_no_shell_and_returns_bounded_output(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()

    class FakeProcess:
        pid = 1234
        def wait(self, timeout=None):
            return 0

    def fake_popen(command, **kwargs):
        assert isinstance(command, list)
        assert "shell" not in kwargs
        kwargs["stdout"].write(b"hello")
        kwargs["stderr"].write(b"")
        return FakeProcess()

    monkeypatch.setattr("core.os_sandbox.subprocess.Popen", fake_popen)
    result = runner().run(("/usr/bin/python3", "-V"), workspace=work,
                          limits=SandboxLimits(output_bytes=4))
    assert result.exit_code == 0
    assert result.stdout == b"hell"
    assert result.output_truncated is True
    assert result.timed_out is False


def test_timeout_kills_process_group(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()

    class FakeProcess:
        pid = 4321
        calls = 0
        def wait(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("bwrap", timeout)
            return -9

    process = FakeProcess()
    monkeypatch.setattr("core.os_sandbox.subprocess.Popen", lambda *a, **k: process)
    killed = []
    monkeypatch.setattr("core.os_sandbox.os.killpg", lambda pid, sig: killed.append((pid, sig)))
    result = runner().run(("/usr/bin/python3", "-V"), workspace=work,
                          limits=SandboxLimits(wall_seconds=1))
    assert result.timed_out is True
    assert killed and killed[0][0] == 4321
