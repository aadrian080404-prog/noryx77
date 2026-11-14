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
