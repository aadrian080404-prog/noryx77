from core.contracts import TaskSpec
from core.planning import Planner
from core.web_research import WebResearchEngine


def _task():
    return TaskSpec("t1", "analysis", "latest NORYX7 architecture", "check current sources", {}, {}, "normal", "exec1")


def test_research_trigger():
    assert WebResearchEngine().should_research(_task())


def test_research_not_needed():
    task = TaskSpec("t2", "analysis", "summarize this text", "hello", {}, {}, "normal", "exec2")
    assert WebResearchEngine().run(task)["status"] == "not_needed"


def test_legacy_planner_remains_single_step():
    plan = Planner(max_steps=2).build(task := TaskSpec("t3", "analysis", "ordinary task", "x", {}, {}, "normal", "exec3"))
    assert len(plan.steps) == 1
