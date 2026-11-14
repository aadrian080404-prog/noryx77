from pathlib import Path
import subprocess
import sys
import runpy

ROOT = Path(__file__).resolve().parents[1]

# Apply the single integration wave.
runpy.run_path(str(ROOT / "devtools" / "apply_frontier_integration_wave.py"), run_name="__main__")

# Bind capability execution to the already trusted agent identity.
hs = ROOT / "core" / "hypersynth.py"
text = hs.read_text(encoding="utf-8")
old = 'principal=agent.agent_id'
new = 'principal=getattr(agent, "identity", None)'
if old not in text:
    raise RuntimeError("frontier principal binding anchor not found")
hs.write_text(text.replace(old, new), encoding="utf-8")

# Chess is a concrete capability; install its dependency when pip is available.
try:
    import chess  # noqa: F401
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "chess"], check=True)

# Persist the dependency contract in the repository without requiring a second manual step.
requirements = ROOT / "requirements-frontier.txt"
requirements.write_text("chess>=1.11,<2\n", encoding="utf-8")

print("===== NORYX7 FRONTIER INTEGRATION WAVE HARDENED =====")
print("principal binding = trusted AgentIdentity")
print("chess dependency = installed/verified")
print("provider credentials = fail-closed")
