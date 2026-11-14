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

def elf64_with_dynamic_dependency(*, needed_offset=1, include_terminator=True, symbol_name_offset=11, symbol_section_index=0):
    ident = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    dynamic = struct.pack("<qQ", 1, needed_offset)
    if include_terminator:
        dynamic += struct.pack("<qQ", 0, 0)
    dynstr = b"\x00libc.so.6\x00puts\x00"
    shstr = b"\x00.dynamic\x00.dynstr\x00.shstrtab\x00.dynsym\x00"
    dynamic_offset = 64
    dynstr_offset = dynamic_offset + len(dynamic)
    shstr_offset = dynstr_offset + len(dynstr)
    symbol_offset = (shstr_offset + len(shstr) + 7) & ~7
    symbols = struct.pack("<IBBHQQ", 0, 0, 0, 0, 0, 0)
    symbols += struct.pack("<IBBHQQ", symbol_name_offset, 0x12, 0, symbol_section_index, 0, 0)
    section_offset = (symbol_offset + len(symbols) + 7) & ~7
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        3, 62, 1, 0, 0, section_offset, 0, 64, 56, 0, 64, 5, 3,
    )
    section_zero = bytes(64)
    dynamic_section = struct.pack(
        "<IIQQQQIIQQ",
        1, 6, 0, 0, dynamic_offset, len(dynamic), 2, 0, 8, 16,
    )
    dynstr_section = struct.pack(
        "<IIQQQQIIQQ",
        10, 3, 0, 0, dynstr_offset, len(dynstr), 0, 0, 1, 0,
    )
    shstr_section = struct.pack(
        "<IIQQQQIIQQ",
        18, 3, 0, 0, shstr_offset, len(shstr), 0, 0, 1, 0,
    )
    dynsym_section = struct.pack(
        "<IIQQQQIIQQ",
        28, 11, 0, 0, symbol_offset, len(symbols), 2, 0, 8, 24,
    )
    payload = ident + header + dynamic + dynstr + shstr
    payload += bytes(symbol_offset - len(payload))
    payload += symbols
    payload += bytes(section_offset - len(payload))
    payload += section_zero + dynamic_section + dynstr_section + shstr_section + dynsym_section
    return payload


def test_elf_dynamic_table_reports_needed_libraries_without_execution():
    report = inspect_elf_bytes(elf64_with_dynamic_dependency())
    assert report.dynamic_libraries == ("libc.so.6",)
    assert any(f.rule_id == "ELF-006" for f in report.findings)


def test_elf_dynamic_table_rejects_out_of_range_string_offsets():
    with pytest.raises(ValueError, match="dynamic_string_offset_invalid"):
        inspect_elf_bytes(elf64_with_dynamic_dependency(needed_offset=99))


def test_elf_dynamic_table_requires_terminator():
    with pytest.raises(ValueError, match="dynamic_table_unterminated"):
        inspect_elf_bytes(elf64_with_dynamic_dependency(include_terminator=False))


def test_elf_dynamic_symbol_table_reports_undefined_imports():
    report = inspect_elf_bytes(elf64_with_dynamic_dependency())
    assert report.dynamic_imports == ("puts",)
    assert any(f.rule_id == "ELF-007" for f in report.findings)


def test_elf_dynamic_symbol_table_rejects_invalid_name_offsets():
    with pytest.raises(ValueError, match="dynamic_symbol_name_offset_invalid"):
        inspect_elf_bytes(elf64_with_dynamic_dependency(symbol_name_offset=99))

def test_elf_dynamic_symbol_table_validates_defined_symbol_name_offsets():
    with pytest.raises(ValueError, match="dynamic_symbol_name_offset_invalid"):
        inspect_elf_bytes(elf64_with_dynamic_dependency(
            symbol_name_offset=99,
            symbol_section_index=1,
        ))
