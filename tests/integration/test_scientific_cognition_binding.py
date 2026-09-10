from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime
from core.scientific_knowledge import ResearchSource
from noryx7_runtime.model_fabric import ModelFabric


class BindingModel:
    name = "binding-model"
    capabilities = frozenset({"text", "reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        return "BOUNDING MODEL OUTPUT"


def test_scientific_sources_reach_uif_and_hypothesis_engine():
    runtime = OperationalNORYXRuntime(model_fabric=ModelFabric([BindingModel()], runtime_id="scientific-binding-test"))
    runtime.scientific_knowledge.add_source(
        ResearchSource(
            source_id="src-physics",
            title="Authorized physics metadata",
            discipline="physics",
            source_type="journal",
            uri="https://example.invalid/physics",
            access_status="metadata_only",
        )
    )
    runtime.scientific_knowledge.add_source(
        ResearchSource(
            source_id="src-math",
            title="Authorized mathematics metadata",
            discipline="mathematics",
            source_type="preprint",
            uri="https://example.invalid/math",
            access_status="metadata_only",
        )
    )
    task = TaskSpec(
        "science-binding",
        "scientific_research",
        "Compare alternative hypotheses about a Navier-Stokes phenomenon",
        "Navier-Stokes turbulence",
        risk_class="normal",
    )
    assessment = runtime.hypersynth.universal_intelligence.branching_engine.explore(task, max_branches=5)
    assert assessment.verification.valid
    assert assessment.source_diversity >= 2
    assert runtime.hypersynth.kernel.hypothesis_engine.branching_engine is runtime.hypersynth.universal_intelligence.branching_engine
    assert runtime.hypersynth.universal_intelligence.branching_engine.source_provider(task)
