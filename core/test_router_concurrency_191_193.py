from concurrent.futures import ThreadPoolExecutor

from .router import ResourceRouter


class DummyAgent:
    def __init__(self, agent_id, model_class="medium", capabilities=()):
        self.agent_id = agent_id
        self.model_class = model_class
        self.capabilities = capabilities
        self.capacity_exempt = False
        self.provider_id = None
        self.model_id = None
        self.provider = None

    def run(self, task):
        return task


def test_attack_191_concurrent_duplicate_registration_is_atomic():
    router = ResourceRouter()
    agents = [DummyAgent("same") for _ in range(32)]

    def register(agent):
        try:
            router.register(agent)
            return "ok"
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(register, agents))

    assert results.count("ok") == 1
    assert results.count("duplicate_agent_id") == 31
    assert router.available() == ("same",)


def test_attack_192_concurrent_reads_and_registrations_never_expose_partial_registry():
    router = ResourceRouter()
    agents = [DummyAgent(f"a{i}") for i in range(20)]

    def register(agent):
        router.register(agent)

    def read():
        return router.available()

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(register, agent) for agent in agents]
        reads = [pool.submit(read) for _ in range(100)]
        for future in futures:
            future.result()
        snapshots = [future.result() for future in reads]

    assert router.available() == tuple(f"a{i}" for i in range(20))
    assert all(snapshot == tuple(sorted(snapshot)) for snapshot in snapshots)
    assert all(set(snapshot).issubset({f"a{i}" for i in range(20)}) for snapshot in snapshots)


def test_attack_193_route_for_task_is_consistent_under_concurrent_registration():
    router = ResourceRouter()
    router.register(DummyAgent("base", model_class="medium"))

    class Task:
        task_type = "general"
        constraints = {}

    agents = [DummyAgent(f"new{i}", model_class="large") for i in range(20)]

    def route():
        agent = router.route_for_task(Task())
        assert agent.agent_id == "base"

    def register(agent):
        router.register(agent)

    with ThreadPoolExecutor(max_workers=21) as pool:
        futures = [pool.submit(route) for _ in range(100)]
        futures += [pool.submit(register, agent) for agent in agents]
        for future in futures:
            future.result()

    assert router.route_for_task(Task()).agent_id == "base"
