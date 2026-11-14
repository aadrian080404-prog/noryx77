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
