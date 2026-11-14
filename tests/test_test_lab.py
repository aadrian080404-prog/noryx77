from pathlib import Path

import pytest

from devtools.test_lab.runner import TestReport, TestResult, allowed_commands, repository_root


def test_test_lab_root_is_repository_root():
    root = repository_root()
    assert (root / "core").is_dir()
    assert (root / "devtools" / "test_lab").is_dir()


def test_test_lab_exposes_only_fixed_targets():
    commands = allowed_commands(Path("."))
    assert set(commands) == {"compile", "pytest", "closure", "completeness"}
    for command in commands.values():
        assert isinstance(command, tuple)
        assert "shell" not in command


def test_test_report_requires_all_selected_results_to_pass():
    passing = TestResult("compile", ("python", "-m", "compileall"), 0, 0.1, "ok")
    report = TestReport(True, 1, 0.1, (passing,))
    assert report.to_dict()["schema"] == "noryx7/test-lab/v1"
    assert report.to_dict()["passed"] is True


def test_unknown_target_is_rejected():
    from devtools.test_lab.runner import run_suite

    with pytest.raises(ValueError, match="unknown_test_target"):
        run_suite(("arbitrary-shell-command",))
