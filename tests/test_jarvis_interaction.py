from jarvis.perception.audio import ClapDetector,AudioEventType
from jarvis.interaction.session import SessionController
from jarvis.agent.front_end import JarvisInteractionFrontEnd

def test_double_clap_activates_only_after_pattern():
    d=ClapDetector(threshold=.8); assert d.register_clap(100,.9) is None
    e=d.register_clap(250,.95); assert e is not None and e.event_type is AudioEventType.CLAP_PATTERN

def test_low_confidence_does_not_activate():
    d=ClapDetector(threshold=.8); assert d.register_clap(100,.79) is None; assert d.register_clap(200,.79) is None

def test_frontend_requires_active_session():
    f=JarvisInteractionFrontEnd()
    try: f.build_input("ciao")
    except PermissionError as e: assert str(e)=="jarvis_session_inactive"
    else: raise AssertionError("inactive session accepted")

def test_wake_then_input():
    d=ClapDetector(); f=JarvisInteractionFrontEnd(SessionController()); e=d.register_clap(100,.9); assert e is None; e=d.register_clap(300,.9); f.on_wake(e,session_id="s1"); assert f.build_input("apri browser").text=="apri browser"
