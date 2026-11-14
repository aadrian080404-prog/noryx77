import os
import struct

import pytest

from core.elf_inspector import inspect_elf_bytes, inspect_elf_file


def elf64(*, program_type=1, flags=3, endian="<"):
    ident = b"\x7fELF" + bytes((2, 1 if endian == "<" else 2, 1)) + bytes(9)
    header = struct.pack(
        endian + "HHIQQQIHHHHHH",
        2, 62, 1, 0x401000, 64, 0, 0, 64, 56, 1, 64, 0, 0,
    )
    program = struct.pack(
        endian + "IIQQQQQQ",
        program_type, flags, 120, 0x401000, 0x401000, 4, 8, 0,
    )
    return ident + header + program + b"DATA"


def elf32():
    ident = b"\x7fELF" + bytes((1, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIIIIIHHHHHH",
        2, 3, 1, 0x8048000, 52, 0, 0, 52, 32, 0, 40, 0, 0,
    )
    return ident + header


def test_elf64_reports_metadata_and_writable_executable_segment():
    report = inspect_elf_bytes(elf64())
    assert report.elf_class == 64
    assert report.endianness == "little"
    assert report.machine == 62
    assert report.entry_point == 0x401000
    assert any(f.rule_id == "ELF-003" and f.severity == "high" for f in report.findings)


def test_elf32_header_is_supported():
    report = inspect_elf_bytes(elf32())
    assert report.elf_class == 32
    assert report.machine == 3
    assert report.program_headers == 0


def test_big_endian_elf_is_parsed():
    report = inspect_elf_bytes(elf64(program_type=1, flags=0, endian=">"))
    assert report.endianness == "big"


def test_executable_gnu_stack_is_reported():
    report = inspect_elf_bytes(elf64(program_type=0x6474E551, flags=1))
    assert any(f.rule_id == "ELF-002" for f in report.findings)


@pytest.mark.parametrize("raw", [b"", b"not-elf", b"\x7fELF" + bytes(12)])
def test_invalid_or_truncated_elf_is_rejected(raw):
    with pytest.raises(ValueError):
        inspect_elf_bytes(raw)


def test_program_header_out_of_bounds_is_rejected():
    raw = bytearray(elf64())
    struct.pack_into("<Q", raw, 32, 0xFFFFFFF0)
    with pytest.raises(ValueError, match="table_out_of_bounds"):
        inspect_elf_bytes(bytes(raw))


def test_segment_payload_out_of_bounds_is_rejected():
    raw = bytearray(elf64())
    struct.pack_into("<Q", raw, 64 + 8, 0xFFFFFFF0)
    with pytest.raises(ValueError, match="segment_out_of_bounds"):
        inspect_elf_bytes(bytes(raw))


def test_table_count_is_bounded():
    raw = bytearray(elf64())
    struct.pack_into("<H", raw, 56, 4097)
    with pytest.raises(ValueError, match="count_limit"):
        inspect_elf_bytes(bytes(raw))


def test_elf_extended_section_count_resolves_then_enforces_parser_limit():
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2, 62, 1, 0, 0, 64, 0, 64, 56, 0, 64, 0, 0,
    )
    # ELF extended section count is stored in sh_size of section header zero.
    section_zero = struct.pack(
        "<IIQQQQIIQQ", 0, 0, 0, 0, 0, 65536, 0, 0, 0, 0,
    )
    with pytest.raises(ValueError, match="section_header_count_limit"):
        inspect_elf_bytes(ident + header + section_zero)


def test_elf_extended_numbering_rejects_non_extended_values():
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2, 62, 1, 0, 0, 64, 0, 64, 56, 0, 64, 0, 0xFFFF,
    )
    section_zero = struct.pack(
        "<IIQQQQIIQQ", 0, 0, 0, 0, 0, 65536, 1, 0, 0, 0,
    )
    with pytest.raises(ValueError, match="extended_string_index_invalid"):
        inspect_elf_bytes(ident + header + section_zero)


def test_elf_extended_program_count_enforces_parser_limit():
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2, 62, 1, 0, 64, 120, 0, 64, 56, 0xFFFF, 64, 1, 0,
    )
    program_zero = struct.pack("<IIQQQQQQ", 0, 0, 0, 0, 0, 0, 0, 0)
    section_zero = struct.pack(
        "<IIQQQQIIQQ", 0, 0, 0, 0, 0, 1, 0, 65535, 0, 0,
    )
    with pytest.raises(ValueError, match="program_header_count_limit"):
        inspect_elf_bytes(ident + header + program_zero + section_zero)

def test_elf_extended_numbering_without_section_zero_is_rejected():
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2, 62, 1, 0, 64, 0, 0, 64, 56, 0xFFFF, 64, 0, 0xFFFF,
    )
    with pytest.raises(ValueError, match="extended_numbering"):
        inspect_elf_bytes(ident + header + bytes(56))



@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_elf_file_inspector_does_not_block_on_non_regular_file(tmp_path):
    fifo = tmp_path / "named-pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular_file"):
        inspect_elf_file(fifo)
