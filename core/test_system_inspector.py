import pytest

from core.system_inspector import PythonSystemInspector


def test_ast_inspector_finds_high_risk_calls_without_executing(tmp_path):
    (tmp_path / "sample.py").write_text(
        "import os\n"
        "os.system('echo no')\n"
        "eval('1 + 1')\n"
        "subprocess.run(['echo', 'x'], shell=True)\n"
        "pickle.loads(blob)\n",
        encoding="utf-8",
    )
    report = PythonSystemInspector().inspect(tmp_path)
    rules = {finding.rule_id for finding in report.findings}
    assert {"PROC-001", "DYN-001", "PROC-002", "DESER-001"} <= rules
    assert report.files_scanned == 1


def test_inspector_does_not_follow_symlinks_or_execute_source(tmp_path):
    target = tmp_path / "outside.py"
    target.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked.py").symlink_to(target)
    (root / "safe.py").write_text("VALUE = 1", encoding="utf-8")
    report = PythonSystemInspector().inspect(root)
    assert report.files_scanned == 1
    assert report.findings == ()


def test_inspector_rejects_symlink_root(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        PythonSystemInspector().inspect(link)


def test_inspector_bounds_file_size_and_reports_parse_errors(tmp_path):
    (tmp_path / "large.py").write_text("x" * 100, encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(:", encoding="utf-8")
    report = PythonSystemInspector(max_file_bytes=20).inspect(tmp_path)
    assert report.files_scanned == 0
    assert any("size_limit_skipped" in item for item in report.parse_errors)
    assert any("parse_error" in item for item in report.parse_errors)


def test_inspector_rejects_invalid_limits():
    with pytest.raises(ValueError, match="invalid_inspector_limit"):
        PythonSystemInspector(max_files=True)
