"""Independent-process regression for durable principal-agent ownership."""
from __future__ import annotations

from multiprocessing import get_all_start_methods, get_context

import pytest

from core.identity import AgentIdentityAuthority
from core.principal_identity import PrincipalIdentity
from core.sqlite_identity import SQLiteIdentityRegistry
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry
from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry


def _bind_in_child(database_path, principal_db, agent_db, principal_id, agent_id, barrier, results):
    principals = SQLitePrincipalIdentityRegistry(principal_db)
    agents = SQLiteIdentityRegistry(agent_db)
    registry = SQLitePrincipalAgentBindingRegistry(
        database_path, principal_registry=principals, agent_registry=agents,
    )
    barrier.wait(timeout=10)
    try:
        registry.bind(principal_id, agent_id)
        results.put(("bound", principal_id))
    except PermissionError:
        results.put(("rejected", principal_id))


def test_two_processes_cannot_claim_the_same_agent_for_different_principals(tmp_path):
    if "fork" not in get_all_start_methods():
        pytest.skip("requires POSIX fork for independent process SQLite test")

    agent, _ = AgentIdentityAuthority.generate("process-race-agent")
    agents = SQLiteIdentityRegistry(tmp_path / "agents.sqlite")
    agents.register(agent)

    principal_one, _ = __import__(
        "core.principal_identity", fromlist=["PrincipalIdentityAuthority"]
    ).PrincipalIdentityAuthority.generate("process-tenant-one")
    principal_two, _ = __import__(
        "core.principal_identity", fromlist=["PrincipalIdentityAuthority"]
    ).PrincipalIdentityAuthority.generate("process-tenant-two")
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite")
    principals.register(principal_one)
    principals.register(principal_two)

    binding_path = tmp_path / "bindings.sqlite"
    first = SQLitePrincipalAgentBindingRegistry(
        binding_path, principal_registry=principals, agent_registry=agents,
    )
    second = SQLitePrincipalAgentBindingRegistry(
        binding_path, principal_registry=principals, agent_registry=agents,
    )
    context = get_context("fork")
    barrier = context.Barrier(2)
    results = context.Queue()
    args = [
        (str(binding_path), str(tmp_path / "principals.sqlite"),
         str(tmp_path / "agents.sqlite"), principal_one.principal_id,
         agent.agent_id, barrier, results),
        (str(binding_path), str(tmp_path / "principals.sqlite"),
         str(tmp_path / "agents.sqlite"), principal_two.principal_id,
         agent.agent_id, barrier, results),
    ]
    processes = [context.Process(target=_bind_in_child, args=item) for item in args]
    for process in processes:
        process.start()
    outcomes = []
    try:
        for _ in processes:
            outcomes.append(results.get(timeout=20))
        for process in processes:
            process.join(timeout=20)
        assert all(process.exitcode == 0 for process in processes)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()

    assert sorted(status for status, _principal in outcomes) == ["bound", "rejected"]
    active = [
        principal_id for principal_id in
        (principal_one.principal_id, principal_two.principal_id)
        if first.is_agent_owned_by_principal(principal_id, agent.agent_id)
    ]
    assert len(active) == 1
    assert active[0] == next(
        principal_id for status, principal_id in outcomes if status == "bound"
    )
