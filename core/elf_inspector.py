"""Bounded, non-executing ELF metadata inspector for authorized review.

This module parses headers and segment/section tables only. It never loads,
maps, imports, or executes the inspected object. Findings are triage signals,
not proof of exploitability or malicious intent.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import struct

MAX_ELF_BYTES = 64 * 1024 * 1024
MAX_TABLE_ENTRIES = 4096
ELF_MAGIC = b"\x7fELF"
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_GNU_STACK = 0x6474E551
PF_X = 1
PF_W = 2
SHT_STRTAB = 3
SHT_DYNAMIC = 6
SHT_DYNSYM = 11
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
MAX_DYNAMIC_ENTRIES = 4096
MAX_DYNAMIC_LIBRARIES = 256
MAX_DYNAMIC_SYMBOLS = 4096


@dataclass(frozen=True, order=True)
class ELFFinding:
    rule_id: str
    severity: str
    evidence: str


@dataclass(frozen=True)
class ELFInspectionReport:
    sha256: str
    size_bytes: int
    elf_class: int
    endianness: str
    object_type: int
    machine: int
    entry_point: int
    program_headers: int
    section_headers: int
    section_names: tuple[str, ...]
    findings: tuple[ELFFinding, ...]
    dynamic_libraries: tuple[str, ...] = ()
    dynamic_imports: tuple[str, ...] = ()


def _bounded_table(data: bytes, offset: int, count: int, entry_size: int,
                   minimum_entry_size: int, label: str) -> None:
    if count > MAX_TABLE_ENTRIES:
        raise ValueError("elf_" + label + "_count_limit")
    if count == 0:
        return
    if entry_size < minimum_entry_size:
        raise ValueError("elf_" + label + "_entry_size_invalid")
    if offset < 0 or offset > len(data) or count * entry_size > len(data) - offset:
        raise ValueError("elf_" + label + "_table_out_of_bounds")


def inspect_elf_bytes(data: bytes) -> ELFInspectionReport:
    if not isinstance(data, bytes):
        raise TypeError("elf_bytes_required")
    if len(data) < 16 or len(data) > MAX_ELF_BYTES:
        raise ValueError("elf_size_invalid")
    if data[:4] != ELF_MAGIC:
        raise ValueError("elf_magic_invalid")
    elf_class, encoding, ident_version = data[4], data[5], data[6]
    if elf_class not in (1, 2) or encoding not in (1, 2) or ident_version != 1:
        raise ValueError("elf_ident_invalid")
    endian = "<" if encoding == 1 else ">"
    endian_name = "little" if encoding == 1 else "big"
    if elf_class == 2:
        header_format = endian + "HHIQQQIHHHHHH"
        header_size = 64
        ph_min, sh_min = 56, 64
        ph_format, sh_format = endian + "IIQQQQQQ", endian + "IIQQQQIIQQ"
    else:
        header_format = endian + "HHIIIIIHHHHHH"
        header_size = 52
        ph_min, sh_min = 32, 40
        ph_format, sh_format = endian + "IIIIIIII", endian + "IIIIIIIIII"
    if len(data) < header_size:
        raise ValueError("elf_header_truncated")
    fields = struct.unpack_from(header_format, data, 16)
    (object_type, machine, version, entry, phoff, shoff, _flags, ehsize,
     phentsize, phnum, shentsize, shnum, shstrndx) = fields
    if version != 1 or ehsize < header_size or ehsize > len(data):
        raise ValueError("elf_header_invalid")
    # ELF extended numbering stores the real counts/indices in section
    # header zero. Resolve it before applying table limits and bounds checks.
    needs_section_zero = (
        (shnum == 0 and shoff != 0)
        or phnum == 0xFFFF
        or shstrndx == 0xFFFF
    )
    section_zero = None
    if needs_section_zero:
        if shoff == 0 or shentsize < sh_min:
            raise ValueError("elf_extended_numbering_section_zero_missing")
        if shoff > len(data) or shentsize > len(data) - shoff:
            raise ValueError("elf_section_header_table_out_of_bounds")
        section_zero = struct.unpack_from(sh_format, data, shoff)
        if elf_class == 2:
            _n, _t, _f, _a, _o, ext_shnum, ext_shstrndx, ext_phnum, _al, _es = section_zero
        else:
            _n, _t, _f, _a, _o, ext_shnum, ext_shstrndx, ext_phnum, _al, _es = section_zero
        if shnum == 0 and shoff != 0:
            if ext_shnum < 0xFF00:
                raise ValueError("elf_extended_section_count_invalid")
            shnum = ext_shnum
        if phnum == 0xFFFF:
            if ext_phnum < 0xFFFF:
                raise ValueError("elf_extended_program_count_invalid")
            phnum = ext_phnum
        if shstrndx == 0xFFFF:
            if ext_shstrndx < 0xFF00:
                raise ValueError("elf_extended_string_index_invalid")
            shstrndx = ext_shstrndx
    elif shnum == 0 and shstrndx != 0:
        raise ValueError("elf_section_name_table_invalid")

    _bounded_table(data, phoff, phnum, phentsize, ph_min, "program_header")
    _bounded_table(data, shoff, shnum, shentsize, sh_min, "section_header")
    if shnum == 0 and shstrndx != 0:
        raise ValueError("elf_section_name_table_invalid")
    findings: list[ELFFinding] = []
    section_names: list[str] = []

    program_segments = []
    for index in range(phnum):
        offset = phoff + index * phentsize
        values = struct.unpack_from(ph_format, data, offset)
        if elf_class == 2:
            p_type, p_flags, p_offset, _vaddr, _paddr, p_filesz, p_memsz, _align = values
        else:
            p_type, p_offset, _vaddr, _paddr, p_filesz, p_memsz, p_flags, _align = values
        if p_filesz > p_memsz or p_offset > len(data) or p_filesz > len(data) - p_offset:
            raise ValueError("elf_segment_out_of_bounds")
        program_segments.append((p_type, p_offset, _vaddr, p_filesz, p_memsz))
        if p_type == PT_INTERP:
            findings.append(ELFFinding("ELF-001", "info", "object declares an interpreter"))
        if p_type == PT_GNU_STACK and p_flags & PF_X:
            findings.append(ELFFinding("ELF-002", "high", "GNU stack segment is executable"))
        if p_type == PT_LOAD and p_flags & PF_W and p_flags & PF_X:
            findings.append(ELFFinding("ELF-003", "high", "loadable segment is writable and executable"))

    section_rows = []
    for index in range(shnum):
        offset = shoff + index * shentsize
        values = struct.unpack_from(sh_format, data, offset)
        if elf_class == 2:
            name_offset, section_type, _flags, _addr, file_offset, size, link, _info, _align, entry_size = values
        else:
            name_offset, section_type, _flags, _addr, file_offset, size, link, _info, _align, entry_size = values
        if section_type != 8 and (file_offset > len(data) or size > len(data) - file_offset):
            raise ValueError("elf_section_out_of_bounds")
        section_rows.append((name_offset, section_type, file_offset, size, link, entry_size))

    if shnum:
        if shstrndx >= shnum:
            raise ValueError("elf_section_name_table_invalid")
        _name_offset, name_type, name_start, name_size, _name_link, _name_entsize = section_rows[shstrndx]
        if name_type == 8 or name_size > MAX_ELF_BYTES:
            raise ValueError("elf_section_name_table_invalid")
        names = data[name_start:name_start + name_size]
        for name_offset, _kind, _start, _size, _link, _entsize in section_rows:
            if name_offset >= len(names):
                if name_offset != 0:
                    raise ValueError("elf_section_name_offset_invalid")
                section_names.append("")
                continue
            end = names.find(b"\x00", name_offset)
            if end < 0:
                raise ValueError("elf_section_name_unterminated")
            try:
                section_names.append(names[name_offset:end].decode("ascii"))
            except UnicodeDecodeError:
                section_names.append("<non-ascii-name>")
        if ".dynamic" in section_names:
            findings.append(ELFFinding("ELF-004", "info", "object contains a dynamic-linking section"))
        if ".debug_info" in section_names or ".symtab" in section_names:
            findings.append(ELFFinding("ELF-005", "info", "debug or full symbol metadata is present"))

    # Resolve DT_NEEDED entries without loading or executing the object.
    # Both the dynamic table and its linked string table remain size-bounded.
    dynamic_libraries: list[str] = []
    dynamic_entry_count = 0
    dynamic_format = endian + ("qQ" if elf_class == 2 else "iI")
    dynamic_entry_size = struct.calcsize(dynamic_format)
    for _name, section_type, file_offset, size, link, entry_size in section_rows:
        if section_type != SHT_DYNAMIC:
            continue
        if (
            entry_size < dynamic_entry_size
            or size % entry_size != 0
            or link >= shnum
        ):
            raise ValueError("elf_dynamic_table_invalid")
        table_entries = size // entry_size
        if dynamic_entry_count + table_entries > MAX_DYNAMIC_ENTRIES:
            raise ValueError("elf_dynamic_table_count_limit")
        dynamic_entry_count += table_entries
        string_section = section_rows[link]
        if string_section[1] != SHT_STRTAB:
            raise ValueError("elf_dynamic_string_table_invalid")
        _string_name, _string_type, string_offset, string_size, _string_link, _string_entsize = string_section
        strings = data[string_offset:string_offset + string_size]
        terminated = False
        for index in range(size // entry_size):
            tag, value = struct.unpack_from(
                dynamic_format, data, file_offset + index * entry_size
            )
            if tag == DT_NULL:
                terminated = True
                break
            if tag != DT_NEEDED:
                continue
            if len(dynamic_libraries) >= MAX_DYNAMIC_LIBRARIES or value >= len(strings):
                raise ValueError("elf_dynamic_string_offset_invalid")
            end = strings.find(b"\x00", value)
            if end < 0:
                raise ValueError("elf_dynamic_string_unterminated")
            try:
                library = strings[value:end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("elf_dynamic_string_encoding_invalid") from exc
            if not library:
                raise ValueError("elf_dynamic_library_name_empty")
            dynamic_libraries.append(library)
        if not terminated:
            raise ValueError("elf_dynamic_table_unterminated")

    # Stripped ELF files may have no section headers. In that case, recover
    # DT_NEEDED from the PT_DYNAMIC segment and map DT_STRTAB through a
    # file-backed PT_LOAD range. This path intentionally does not infer
    # dynamic-symbol counts or imports.
    if not any(row[1] == SHT_DYNAMIC for row in section_rows):
        dynamic_segments = [row for row in program_segments if row[0] == PT_DYNAMIC]
        if len(dynamic_segments) > 1:
            raise ValueError("elf_multiple_dynamic_segments")
        if dynamic_segments:
            _kind, dynamic_offset, _dynamic_vaddr, dynamic_size, _dynamic_memsz = dynamic_segments[0]
            if dynamic_size % dynamic_entry_size != 0:
                raise ValueError("elf_dynamic_segment_size_invalid")
            segment_entries = dynamic_size // dynamic_entry_size
            if segment_entries > MAX_DYNAMIC_ENTRIES:
                raise ValueError("elf_dynamic_table_count_limit")
            tags = []
            needed_offsets = []
            terminated = False
            for index in range(segment_entries):
                tag, value = struct.unpack_from(
                    dynamic_format, data, dynamic_offset + index * dynamic_entry_size
                )
                if tag == DT_NULL:
                    terminated = True
                    break
                tags.append((tag, value))
                if tag == DT_NEEDED:
                    if len(needed_offsets) >= MAX_DYNAMIC_LIBRARIES:
                        raise ValueError("elf_dynamic_string_offset_invalid")
                    needed_offsets.append(value)
            if not terminated:
                raise ValueError("elf_dynamic_table_unterminated")
            if needed_offsets:
                strtab_values = [value for tag, value in tags if tag == DT_STRTAB]
                strsz_values = [value for tag, value in tags if tag == DT_STRSZ]
                if len(strtab_values) != 1 or len(strsz_values) != 1:
                    raise ValueError("elf_dynamic_string_table_invalid")
                string_vaddr, string_size = strtab_values[0], strsz_values[0]
                if string_size > MAX_ELF_BYTES:
                    raise ValueError("elf_dynamic_string_table_limit")
                string_file_offset = None
                for kind, file_offset, virtual_address, file_size, _memory_size in program_segments:
                    if kind != PT_LOAD or string_vaddr < virtual_address:
                        continue
                    delta = string_vaddr - virtual_address
                    if delta <= file_size and string_size <= file_size - delta:
                        string_file_offset = file_offset + delta
                        break
                if string_file_offset is None:
                    raise ValueError("elf_dynamic_string_table_unmapped")
                strings = data[string_file_offset:string_file_offset + string_size]
                for value in needed_offsets:
                    if value >= len(strings):
                        raise ValueError("elf_dynamic_string_offset_invalid")
                    end = strings.find(b"\\x00", value)
                    if end < 0:
                        raise ValueError("elf_dynamic_string_unterminated")
                    try:
                        library = strings[value:end].decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ValueError("elf_dynamic_string_encoding_invalid") from exc
                    if not library:
                        raise ValueError("elf_dynamic_library_name_empty")
                    dynamic_libraries.append(library)

    if dynamic_libraries:
        findings.append(ELFFinding(
            "ELF-006", "info",
            "dynamic dependencies: " + ", ".join(dynamic_libraries[:8]),
        ))

    # Resolve undefined dynamic symbols as import metadata. Symbol tables are
    # never interpreted as code and every name is checked against its linked
    # bounded string table.
    dynamic_imports: list[str] = []
    dynamic_symbol_entry_count = 0
    symbol_format = endian + ("IBBHQQ" if elf_class == 2 else "IIIBBH")
    minimum_symbol_size = struct.calcsize(symbol_format)
    for _name, section_type, file_offset, size, link, entry_size in section_rows:
        if section_type != SHT_DYNSYM:
            continue
        if (
            entry_size < minimum_symbol_size
            or size % entry_size != 0
            or link >= shnum
        ):
            raise ValueError("elf_dynamic_symbol_table_invalid")
        table_symbols = size // entry_size
        if dynamic_symbol_entry_count + table_symbols > MAX_DYNAMIC_SYMBOLS:
            raise ValueError("elf_dynamic_symbol_count_limit")
        dynamic_symbol_entry_count += table_symbols
        string_section = section_rows[link]
        if string_section[1] != SHT_STRTAB:
            raise ValueError("elf_dynamic_symbol_string_table_invalid")
        _str_name, _str_type, string_offset, string_size, _str_link, _str_entsize = string_section
        symbol_strings = data[string_offset:string_offset + string_size]
        for index in range(size // entry_size):
            values = struct.unpack_from(
                symbol_format, data, file_offset + index * entry_size
            )
            if elf_class == 2:
                name_offset, _info, _other, section_index, _value, _symbol_size = values
            else:
                name_offset, _value, _symbol_size, _info, _other, section_index = values
            if name_offset == 0:
                continue
            if name_offset >= len(symbol_strings):
                raise ValueError("elf_dynamic_symbol_name_offset_invalid")
            end = symbol_strings.find(b"\x00", name_offset)
            if end < 0:
                raise ValueError("elf_dynamic_symbol_name_unterminated")
            name = symbol_strings[name_offset:end].decode("utf-8", "replace")
            if not name:
                raise ValueError("elf_dynamic_symbol_name_empty")
            if section_index == 0:
                if len(dynamic_imports) >= MAX_DYNAMIC_SYMBOLS:
                    raise ValueError("elf_dynamic_symbol_count_limit")
                dynamic_imports.append(name)
    if dynamic_imports:
        findings.append(ELFFinding(
            "ELF-007", "info",
            "undefined dynamic symbols: " + ", ".join(dynamic_imports[:8]),
        ))

    return ELFInspectionReport(
        hashlib.sha256(data).hexdigest(), len(data), 64 if elf_class == 2 else 32,
        endian_name, object_type, machine, entry, phnum, shnum,
        tuple(section_names), tuple(sorted(set(findings))),
        tuple(dynamic_libraries), tuple(dynamic_imports),
    )


def inspect_elf_file(path: str | os.PathLike[str], *, max_bytes: int = MAX_ELF_BYTES) -> ELFInspectionReport:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_ELF_BYTES:
        raise ValueError("elf_file_limit_invalid")
    target = Path(path)
    if target.is_symlink():
        raise ValueError("elf_path_must_not_be_symlink")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(target, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("elf_path_must_be_regular_file")
        if metadata.st_size > max_bytes:
            raise ValueError("elf_file_size_limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("elf_file_size_limit")
    finally:
        os.close(descriptor)
    return inspect_elf_bytes(raw)
