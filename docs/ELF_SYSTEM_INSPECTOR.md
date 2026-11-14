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


## Unified system inspection

PythonSystemInspector.inspect(root) now recognizes ELF files by their magic
header alongside .py sources. Python AST findings and ELF structural findings
are returned in the same deterministic finding list; detailed ELF metadata is
also available through InspectionReport.binary_reports, including bounded `DT_NEEDED` library names from each ELF report. The same file-count,
per-file byte and aggregate byte budgets apply. Other binary formats are
skipped rather than guessed or executed.

The tree walk consumes directory entries incrementally and applies a global
entry budget, including irrelevant files and directories. Reaching that budget
adds `entry_limit_reached`; the report must then be treated as partial, not as
a complete inventory. File opens use no-follow, nonblocking and close-on-exec
flags where supported, and the actual bytes read are bounded against both the
per-file and remaining aggregate budgets. Metadata size is only an early
rejection hint; it is not trusted as the sole byte-budget enforcement.

The path walk is intended for a trusted or immutable inspection workspace.
No-follow file opens protect the final file component, but this implementation
does not provide an `openat2(RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS)`-style
guarantee against a hostile process concurrently replacing parent directories.
For adversarial live filesystems, inspect a read-only snapshot or add a
platform-specific directory-descriptor traversal before treating path
containment as a security boundary.

The integrated report now exposes bounded ELF `DT_NEEDED` library names and undefined dynamic symbol names from `SHT_DYNSYM` tables. These are static metadata only: no binary, dependency, or symbol is loaded or executed.

The current dependency and dynamic-import extraction uses bounded section
headers (`SHT_DYNAMIC` and `SHT_DYNSYM`). It does not yet reconstruct these
tables from `PT_DYNAMIC` when section headers are absent (for example, some
stripped binaries); such files may still contain dynamic dependencies that
this version does not report. Treat an empty dependency/import list as
'information not found by this parser', not proof that the ELF has none.

Dynamic table and dynamic-symbol entry budgets are aggregate across all
matching sections, not merely per section: at most 4096 dynamic entries,
4096 dynamic symbols, and 256 dependency names are processed per ELF.
