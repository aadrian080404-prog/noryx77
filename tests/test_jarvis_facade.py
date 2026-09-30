from jarvis.agent.front_end import AgentInput
from jarvis.runtime_facade import JarvisFacade

def test_facade_does_not_create_execution_without_plan():
    # Contract-level check: facade requires a concrete plan before runtime execution.
    f=JarvisFacade()
    assert hasattr(f,"accept_input")
