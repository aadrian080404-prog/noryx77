from core.provider_router import Provider, ProviderRouter
from core.job_supervisor import JobSupervisor, JobStatus
from core.device_fabric import Device, DeviceFabric
from core.multimodal import MediaRef, Modality, MultimodalInput
from core.tool_protocol import ToolRegistry, ToolSpec

def test_provider_failover():
    r=ProviderRouter()
    r.register(Provider("bad",frozenset({"chat"}),lambda _: (_ for _ in ()).throw(RuntimeError())))
    r.register(Provider("good",frozenset({"chat"}),lambda x: x["ok"]))
    assert r.execute("chat",{"ok":7})==7

def test_job_supervisor_bounded_retry():
    s=JobSupervisor(max_attempts=2); s.submit("j")
    assert s.run("j",lambda: (_ for _ in ()).throw(ValueError())).status==JobStatus.FAILED
    assert s.run("j",lambda: 3).result==3

def test_device_fabric_requires_online_capability():
    f=DeviceFabric(); f.register(Device("phone",frozenset({"camera"})))
    assert f.resolve("camera").device_id=="phone"
    f.set_online("phone",False)
    try: f.resolve("camera"); assert False
    except LookupError: pass

def test_multimodal_digest_and_tool_authorization():
    m=MediaRef.create(Modality.IMAGE,"image/png","ref://1",b"x")
    assert len(m.digest)==64
    assert len(MultimodalInput.build((m,)).request_digest)==64
    t=ToolRegistry(); t.register(ToolSpec("echo","1",frozenset({"test"}),lambda a:a["x"]))
    assert t.invoke("echo",{"x":1},authorize=lambda _:False).error=="authorization_denied"
    assert t.invoke("echo",{"x":1},authorize=lambda _:True).value==1
