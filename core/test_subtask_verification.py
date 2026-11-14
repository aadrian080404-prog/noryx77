import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .decomposition import Subtask
from .subtask_uif import SubtaskRoute, SubtaskRouteSet, SubtaskUIFRouter
from .subtask_verification import verify_subtasks
from .universal_intelligence import SpecialistRoute, UniversalIntelligenceFabric


class SubtaskVerificationTests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec("compound", "research", "compound objective", "input", risk_class="normal", execution_id="exec-1")
        subtasks = (
            Subtask("compound:0", "collect scientific evidence", "research"),
            Subtask("compound:1", "compare financial evidence", "research", ("compound:0",)),
        )
        self.routes = SubtaskUIFRouter(UniversalIntelligenceFabric()).route(self.task, subtasks)

    def result(self, task_id, output="ok", valid=True):
        return AgentResult("agent-" + task_id[-1], task_id, "completed", output, VerificationResult(valid, "agent_result", "ok" if valid else "bad"), "exec-1")

    def test_exact_ordered_coverage_is_commit_eligible(self):
        gate = verify_subtasks(self.routes, (self.result("compound:0"), self.result("compound:1")))
        self.assertTrue(gate.commit_eligible)
        self.assertEqual(gate.verification.reason, "subtask_commit_gate_ok")
        self.assertEqual(tuple(item.subtask_id for item in gate.evidence), ("compound:0", "compound:1"))

    def test_missing_subtask_blocks_commit(self):
        gate = verify_subtasks(self.routes, (self.result("compound:0"),))
        self.assertFalse(gate.commit_eligible)
        self.assertEqual(gate.verification.reason, "subtask_result_coverage_mismatch")

    def test_unverified_subtask_blocks_commit(self):
        gate = verify_subtasks(self.routes, (self.result("compound:0"), self.result("compound:1", valid=False)))
        self.assertFalse(gate.commit_eligible)
        self.assertEqual(gate.verification.reason, "subtask_unverified")

    def test_duplicate_subtask_result_blocks_commit(self):
        gate = verify_subtasks(self.routes, (self.result("compound:0"), self.result("compound:0")))
        self.assertFalse(gate.commit_eligible)
        self.assertEqual(gate.verification.reason, "subtask_result_identity_invalid")

    def test_route_contract_never_grants_authority(self):
        route = self.routes.routes[0]
        self.assertFalse(route.route_authority)
        self.assertTrue(route.is_well_formed())
        constraints = SubtaskUIFRouter.constraints_for(self.task, route)
        self.assertIs(constraints["_noryx7_route_authority"], False)

    def test_authoritative_route_object_is_rejected(self):
        route = self.routes.routes[0]
        bad = SubtaskRoute(route.subtask_id, route.route, True)
        bad_set = SubtaskRouteSet(self.routes.task_id, (bad,) + self.routes.routes[1:], self.routes.verification)
        gate = verify_subtasks(bad_set, (self.result("compound:0"), self.result("compound:1")))
        self.assertFalse(gate.commit_eligible)
        self.assertEqual(gate.verification.reason, "subtask_routes_invalid")


if __name__ == "__main__":
    unittest.main()
