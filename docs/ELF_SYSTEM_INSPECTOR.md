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


## Unified system inspection

PythonSystemInspector.inspect(root) now recognizes ELF files by their magic
header alongside .py sources. Python AST findings and ELF structural findings
are returned in the same deterministic finding list; detailed ELF metadata is
also available through InspectionReport.binary_reports. The same file-count,
per-file byte and aggregate byte budgets apply. Other binary formats are
skipped rather than guessed or executed.
