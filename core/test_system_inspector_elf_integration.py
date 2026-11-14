import struct

from core.system_inspector import PythonSystemInspector


def executable_writable_elf64():
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2, 62, 1, 0x401000, 64, 0, 0, 64, 56, 1, 64, 0, 0,
    )
    program = struct.pack(
        "<IIQQQQQQ", 1, 3, 120, 0x401000, 0x401000, 4, 8, 0,
    )
    return ident + header + program + b"DATA"


def test_unified_inspector_scans_python_and_elf_without_execution(tmp_path):
    (tmp_path / "unsafe.py").write_text("import os\nos.system('example')\n")
    (tmp_path / "sample.bin").write_bytes(executable_writable_elf64())

    report = PythonSystemInspector().inspect(tmp_path)

    assert report.files_scanned == 2
    assert len(report.binary_reports) == 1
    assert report.binary_reports[0].machine == 62
    assert any(f.path == "unsafe.py" and f.rule_id == "PROC-001" for f in report.findings)
    assert any(f.path == "sample.bin" and f.rule_id == "ELF-003" for f in report.findings)
    assert report.parse_errors == ()


def test_unified_inspector_skips_non_elf_binary_files(tmp_path):
    (tmp_path / "notes.bin").write_bytes(b"ordinary data")
    report = PythonSystemInspector().inspect(tmp_path)
    assert report.files_scanned == 0
    assert report.binary_reports == ()
    assert report.findings == ()


def test_malformed_python_still_consumes_file_and_byte_budgets(tmp_path):
    malformed = b"def broken(:\n"
    (tmp_path / "a.py").write_bytes(malformed)
    (tmp_path / "b.py").write_text("x = 1\n")

    report = PythonSystemInspector(max_files=1).inspect(tmp_path)

    assert report.files_scanned == 1
    assert report.bytes_scanned == len(malformed)
    assert any(error.endswith(":SyntaxError") for error in report.parse_errors)
    assert "file_limit_reached" in report.parse_errors


def test_malformed_elf_still_consumes_file_and_byte_budgets(tmp_path):
    malformed = b"\x7fELF" + bytes(12)
    (tmp_path / "a.bin").write_bytes(malformed)
    (tmp_path / "b.py").write_text("x = 1\n")

    report = PythonSystemInspector(max_files=1).inspect(tmp_path)

    assert report.files_scanned == 1
    assert report.bytes_scanned == len(malformed)
    assert any(error.endswith(":ValueError") for error in report.parse_errors)
    assert "file_limit_reached" in report.parse_errors


def test_malformed_source_cannot_bypass_total_byte_budget(tmp_path):
    malformed = b"not valid python"
    (tmp_path / "a.py").write_bytes(malformed)
    (tmp_path / "b.py").write_text("x = 1\n")

    report = PythonSystemInspector(max_total_bytes=len(malformed)).inspect(tmp_path)

    assert report.files_scanned == 1
    assert report.bytes_scanned == len(malformed)
    assert any(error.endswith(":SyntaxError") for error in report.parse_errors)
    assert any(error.startswith("size_limit_skipped:b.py") for error in report.parse_errors)


def test_inspector_bounds_directory_entries_including_irrelevant_files(tmp_path):
    for name in ("a.bin", "b.bin", "c.bin"):
        (tmp_path / name).write_bytes(b"ordinary non-ELF data")
    report = PythonSystemInspector(max_entries=2).inspect(tmp_path)
    assert report.files_scanned == 0
    assert "entry_limit_reached" in report.parse_errors


def test_inspector_validates_entry_budget():
    import pytest
    with pytest.raises(ValueError, match="max_entries"):
        PythonSystemInspector(max_entries=True)


def test_inspector_stops_enumerating_directory_at_entry_budget(tmp_path, monkeypatch):
    import os
    import core.system_inspector as inspector_module

    for index in range(20):
        (tmp_path / f"irrelevant-{index:02}.bin").write_bytes(b"data")

    real_scandir = os.scandir
    yielded = {"count": 0}

    class CountingScandir:
        def __init__(self, path):
            self._iterator = real_scandir(path)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self._iterator.close()

        def __iter__(self):
            for entry in self._iterator:
                yielded["count"] += 1
                yield entry

    monkeypatch.setattr(inspector_module.os, "scandir", CountingScandir)
    report = PythonSystemInspector(max_entries=3).inspect(tmp_path)

    assert yielded["count"] == 4
    assert "entry_limit_reached" in report.parse_errors



def test_inspector_enforces_actual_read_budget_when_file_grows_after_stat(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace
    import core.system_inspector as inspector_module

    (tmp_path / "growing.py").write_bytes(b"x = 123456789\\n")
    real_fstat = os.fstat

    def understated_fstat(descriptor):
        metadata = real_fstat(descriptor)
        return SimpleNamespace(st_mode=metadata.st_mode, st_size=1)

    monkeypatch.setattr(inspector_module.os, "fstat", understated_fstat)
    report = PythonSystemInspector(max_file_bytes=32, max_total_bytes=4).inspect(tmp_path)

    assert report.files_scanned == 0
    assert report.bytes_scanned == 0
    assert any(error.startswith("size_limit_skipped:growing.py") for error in report.parse_errors)


def test_inspector_opens_child_files_relative_to_pinned_directory_fd(tmp_path, monkeypatch):
    import os
    import core.system_inspector as inspector_module

    (tmp_path / "probe.py").write_text("value = 1\\n")
    real_open = os.open
    relative_opens = []

    def tracked_open(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            relative_opens.append(path)
            return real_open(path, flags, mode, dir_fd=dir_fd)
        return real_open(path, flags, mode)

    monkeypatch.setattr(inspector_module.os, "open", tracked_open)
    report = PythonSystemInspector().inspect(tmp_path)

    assert report.files_scanned == 1
    assert "probe.py" in relative_opens


def test_inspector_does_not_follow_symlinked_directory_or_file(tmp_path):
    import os
    import pytest

    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (outside / "secret.py").write_text("import os\\nos.system('must-not-be-scanned')\\n")
    (tmp_path / "inside.py").write_text("safe = True\\n")
    try:
        (tmp_path / "linked-dir").symlink_to(outside, target_is_directory=True)
        (tmp_path / "linked-file.py").symlink_to(outside / "secret.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")

    report = PythonSystemInspector().inspect(tmp_path)

    assert report.files_scanned == 1
    assert not any(f.path.startswith("linked-dir/") for f in report.findings)
    assert not any(f.path == "linked-file.py" for f in report.findings)
    assert not any(f.rule_id == "PROC-001" for f in report.findings)


def test_inspector_rejects_symlinked_ancestor_of_root(tmp_path):
    import pytest

    real_parent = tmp_path / "real-parent"
    real_root = real_parent / "tree"
    real_root.mkdir(parents=True)
    (real_root / "safe.py").write_text("safe = True\\n")
    alias = tmp_path / "alias-parent"
    try:
        alias.symlink_to(real_parent, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")

    with pytest.raises(OSError):
        PythonSystemInspector().inspect(alias / "tree")
