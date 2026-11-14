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

Dependency extraction first uses bounded `SHT_DYNAMIC` sections and
falls back to `PT_DYNAMIC` plus an unambiguous file-backed `PT_LOAD` mapping
when section headers are absent. For stripped objects, undefined imports are
also recovered when the dynamic table supplies a bounded SysV `DT_HASH` or GNU
`DT_GNU_HASH`, together with `DT_SYMTAB` and `DT_SYMENT`. GNU hash buckets
and chains are traversed under the 4096-symbol bound. Dynamic relocation
reconstruction and relocation target analysis remain unsupported. Ambiguous virtual-address mappings, malformed hash tables,
oversized symbol counts, and invalid string offsets fail closed. An empty
dependency/import list means 'not found by this parser', not proof that the
ELF has none.

Dynamic table and dynamic-symbol entry budgets are aggregate across all
matching sections, not merely per section: at most 4096 dynamic entries,
4096 dynamic symbols, and 256 dependency names are processed per ELF.
