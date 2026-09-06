from ecosystem.boundaries import Front, make_intent
from ecosystem.front_runtime import hypersynth
class Runtime:
    def run(self, task, interaction_context):
        return {"status":"completed","task":task,"context":interaction_context}
def test_hypersynth_adapter_binds_concrete_runtime_to_dispatch():
    intent=make_intent(Front.ORCHESTRATION,"run",b"x")
    result=hypersynth(intent,"e1",Runtime(),"task","ctx")
    assert result.receipt.accepted
    assert result.value["status"]=="completed"
