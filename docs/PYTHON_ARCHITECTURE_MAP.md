# Static Python architecture mapping

`PythonArchitectureMapper` performs bounded AST inspection without importing,
executing, or modifying the inspected project. It produces:

- a deterministic Python module inventory;
- static import relationships between modules in the inspected root;
- standard-library and third-party top-level dependency inventories;
- class/function definitions and `__main__` entrypoint markers;
- capability-surface hints for process execution, filesystem access, native
  FFI, deserialization, dynamic imports, networking, and TLS;
- bounded parse and size-limit diagnostics.

This is a source-level architecture map, not a universal reverse-engineering
engine. It does not analyze binaries, runtime behavior, encrypted traffic,
protocol state machines, or non-Python languages. Static import edges may miss
dynamic imports and runtime-generated modules. Findings are navigational
evidence for authorized review, not proof of exploitability.
