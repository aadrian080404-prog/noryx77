from ecosystem.global_scale import (
    Capacity,
    Cell,
    CellRegistry,
    DegradationController,
    DegradationMode,
    DisasterRecoveryPlan,
    ElasticComputeFabric,
    EventFabric,
    GlobalControlPlane,
    GlobalTrafficRouter,
    Health,
    LanguageContext,
    LanguageFabric,
    ResourceBudget,
    ResourceController,
    SelfHealingController,
    SyntheticTestingGrid,
    WorkClass,
    WorkRequest,
)


def test_global_router_selects_healthy_region_and_cell():
    control = GlobalControlPlane()
    cells = CellRegistry()
    capacity = Capacity(10, 4, 100, 100)
    control.register(__import__('ecosystem.global_scale', fromlist=['Region']).Region('eu', latency_ms=10, capacity=capacity))
    cells.register(Cell('eu-1', 'eu', capacity=capacity))
    route = GlobalTrafficRouter(control, cells).route(WorkRequest('r1', Capacity(1, 1, 1, 1), WorkClass.REALTIME))
    assert (route.region_id, route.cell_id, route.degradation) == ('eu', 'eu-1', DegradationMode.FULL)


def test_failed_region_can_fail_over_without_being_selected():
    plan = DisasterRecoveryPlan()
    c = Capacity(5, 2, 10, 10)
    from ecosystem.global_scale import Region
    regions = (Region('eu', Health.OFFLINE, 1, c), Region('us', Health.HEALTHY, 20, c))
    assert plan.choose(regions, 'eu', Capacity(1, 1, 1, 1)).region_id == 'us'


def test_event_fabric_is_bounded_and_priority_ordered():
    q = EventFabric(max_items=2)
    q.publish(WorkRequest('a', Capacity(1,0,1,1), WorkClass.ASYNC, priority=1), 'a')
    q.publish(WorkRequest('b', Capacity(1,0,1,1), WorkClass.ASYNC, priority=5), 'b')
    assert [x.payload for x in q.drain(2)] == ['b', 'a']
    try:
        q.publish(WorkRequest('c', Capacity(1,0,1,1), WorkClass.ASYNC), 'c')
    except MemoryError:
        pass
    else:
        raise AssertionError('queue must be empty after drain')


def test_compute_fabric_accounts_for_capacity():
    fabric = ElasticComputeFabric()
    fabric.register_worker_pool('p1', Capacity(4, 2, 10, 10))
    assert fabric.acquire(Capacity(2, 1, 4, 4)) == 'p1'
    fabric.release('p1', Capacity(2, 1, 4, 4))


def test_language_and_resource_boundaries():
    context = LanguageContext('it', 'it', ('de',), 'it-IT', 'Europe/Rome')
    envelope = LanguageFabric().normalize('documento tedesco', context)
    assert len(envelope.semantic_digest) == 64
    ResourceController().admit(ResourceBudget(10, 10, 10, 10, 2, 10), used=ResourceBudget(1,1,1,1,1,1))


def test_degradation_and_self_healing_fail_closed():
    degradation = DegradationController()
    degradation.set_mode(DegradationMode.QUEUE)
    try:
        degradation.require_available(WorkClass.REALTIME)
    except PermissionError:
        pass
    else:
        raise AssertionError('realtime work must not bypass queue mode')
    healing = SelfHealingController()
    for stage in ('detected', 'diagnosed', 'proposed', 'sandboxed', 'verified', 'canary', 'deployed'):
        healing.advance('component', stage)
    healing.rollback('component')
    assert healing.stage('component') is None


def test_synthetic_grid_is_deterministic_and_bounded():
    grid = SyntheticTestingGrid(10)
    first = grid.generate(42, 3)
    second = grid.generate(42, 3)
    assert first == second
    assert len(first) == 3
