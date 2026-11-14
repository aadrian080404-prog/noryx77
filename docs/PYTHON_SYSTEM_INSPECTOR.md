# Python system inspector

This authorized-review helper walks a bounded source tree, skips symlinks and
common generated/vendor directories, and parses Python source using the AST.
It does not import, execute, modify or transmit inspected code.

Current rules flag selected dynamic execution, shell process APIs, unsafe
deserialization primitives, legacy hash APIs and disabled TLS verification.
Reports include deterministic source paths and line numbers.

Findings are heuristic review leads, not proof of a vulnerability. The scanner
does not understand runtime data flow, native binaries, compiled extensions,
protocol behavior, authorization semantics or exploitability. It is not a
replacement for SAST, dependency scanning, fuzzing, sandboxed dynamic testing
or human review. Scope and size limits are enforced to bound resource use.
