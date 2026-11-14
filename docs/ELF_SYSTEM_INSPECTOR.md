# Bounded ELF System Inspector

`core.elf_inspector` performs static, non-executing inspection of ELF
metadata for authorized system review. It supports ELF32 and ELF64, both byte
orders, validates program/section table bounds, rejects oversized tables and
segments outside the supplied file, and reports selected structural signals:
executable GNU stack, writable+executable load segments, interpreter presence,
dynamic-linking sections, debug/full-symbol metadata, and bounded `DT_NEEDED` dependency names from linked dynamic/string tables.

The parser accepts bytes or a regular file opened without following symlinks. Dynamic tables are limited to 4096 entries and 256 dependency names; malformed or unterminated tables and out-of-range string offsets are rejected. Dependency names are metadata only and are never loaded.
It does not execute, load, map, disassemble, resolve imports, or determine
whether a binary is malicious. Findings are triage leads; benign software can
have the same properties. Unknown formats and malformed bounds fail closed.

Default maximum input is 64 MiB and program/section tables are capped at 4096
entries. For dynamic analysis, use a separately provisioned, disposable
sandbox with kernel-enforced isolation; never execute unknown binaries as part
of static inspection.

The inspector also resolves bounded `DT_NEEDED` names through the linked dynamic string table. It now reads undefined dynamic symbol names from bounded `SHT_DYNSYM` tables as import metadata; malformed offsets, invalid links, and oversized tables are rejected. Neither dependencies nor symbols are loaded or executed.

The current dependency and dynamic-import extraction uses bounded section
headers (`SHT_DYNAMIC` and `SHT_DYNSYM`). It does not yet reconstruct these
tables from `PT_DYNAMIC` when section headers are absent (for example, some
stripped binaries); such files may still contain dynamic dependencies that
this version does not report. Treat an empty dependency/import list as
'information not found by this parser', not proof that the ELF has none.
