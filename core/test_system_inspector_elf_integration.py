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
