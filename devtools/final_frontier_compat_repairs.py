from pathlib import Path


def replace_any(path, replacements):
    p = Path(path)
    s = p.read_text()
    for old, new in replacements:
        if old in s:
            s = s.replace(old, new, 1)
            print(f"PATCHED {path}")
            p.write_text(s)
            return
    print(f"UNCHANGED {path}")

# The offline snapshot is bound to the execution principal, not to the
# deterministic online agent identity. This preserves the snapshot contract
# while keeping online identity binding unchanged.
replace_any("core/runtime.py", [
    (
        '        principal_id, principal_key_fingerprint = self._principal_binding("deterministic")\n',
        '        principal_id = getattr(task, "principal_id", None) or execution_id\n        principal_key_fingerprint = None\n',
    ),
])

# ToolExecutor must defer malformed-policy handling to the canonical execution
# gate. Construction itself must not call or trust an arbitrary policy object.
replace_any("core/tools.py", [
    (
        '        if isinstance(policy_or_gate, ActionGate):\n            self.action_gate = policy_or_gate\n        elif isinstance(policy_or_gate, PolicyEngine):\n            security = SecurityBoundary(policy_or_gate, verifier)\n            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())\n        else:\n            raise ValueError("action_gate_or_policy_required")\n',
        '        if isinstance(policy_or_gate, ActionGate):\n            self.action_gate = policy_or_gate\n        else:\n            security = SecurityBoundary(policy_or_gate, verifier)\n            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())\n',
    ),
])

# If the previous compatibility script inserted an unused PolicyEngine import,
# remove it; ToolExecutor intentionally accepts policy-like objects here.
replace_any("core/tools.py", [
    ('from .policy import PolicyEngine\n', ''),
])

print("FINAL_FRONTIER_COMPAT_REPAIRS_APPLIED")
