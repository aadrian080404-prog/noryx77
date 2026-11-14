# Bounded ELF System Inspector

`core.elf_inspector` performs static, non-executing inspection of ELF
metadata for authorized system review. It supports ELF32 and ELF64, both byte
orders, validates program/section table bounds, rejects oversized tables and
segments outside the supplied file, and reports selected structural signals:
executable GNU stack, writable+executable load segments, interpreter presence,
dynamic-linking sections, and debug/full-symbol metadata.

The parser accepts bytes or a regular file opened without following symlinks.
It does not execute, load, map, disassemble, resolve imports, or determine
whether a binary is malicious. Findings are triage leads; benign software can
have the same properties. Unknown formats and malformed bounds fail closed.

Default maximum input is 64 MiB and program/section tables are capped at 4096
entries. For dynamic analysis, use a separately provisioned, disposable
sandbox with kernel-enforced isolation; never execute unknown binaries as part
of static inspection.
