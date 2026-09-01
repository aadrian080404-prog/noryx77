import unittest

from core.attestation import HypersynthAttestation
from core.contracts import TaskSpec
from core.crypto import CryptoIntegrity
from core.kernel_continuity import KernelContinuity, KernelContinuityRecord


class KernelContinuityTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)
        self.task = TaskSpec("continuity", "research", "objective", "input", risk_class="normal")
        self.attestation = HypersynthAttestation(self.crypto)
        self.stage = self.attestation.attest_stage(
            self.task.task_id, "planning", self.task.risk_class,
            self.task.verification_requirements, {"plan": "p1"}
        )
        self.continuity = KernelContinuity(
            self.crypto,
            session_id="session-1",
            task_id=self.task.task_id,
            risk_class=self.task.risk_class,
            verification_requirements=self.task.verification_requirements,
        )

    def test_attack71_state_snapshot_tamper_rejected(self):
        record = self.continuity.attest("planning", {"state": "before"}, {"plan": "input"}, {"plan": "output"}, dependency_tag=self.stage.tag)
        self.assertTrue(self.continuity.verify(record, "planning", {"state": "before"}, {"plan": "input"}, {"plan": "output"}, dependency_tag=self.stage.tag, previous_tag="", sequence=1))
        self.assertFalse(self.continuity.verify(record, "planning", {"state": "tampered"}, {"plan": "input"}, {"plan": "output"}, dependency_tag=self.stage.tag, previous_tag="", sequence=1))

    def test_attack72_previous_state_transition_fork_rejected(self):
        first = self.continuity.attest("context", {"s": 1}, {"i": 1}, {"o": 1}, dependency_tag=self.stage.tag)
        second = self.continuity.attest("planning", {"s": 2}, {"i": 2}, {"o": 2}, dependency_tag=first.tag)
        self.assertFalse(self.continuity.verify(second, "planning", {"s": 2}, {"i": 2}, {"o": 2}, dependency_tag=first.tag, previous_tag="0" * 64, sequence=2))

    def test_attack73_plan_dependency_bound_to_authenticated_stage(self):
        record = self.continuity.attest("planning", {"state": 1}, {"context": "ctx"}, {"plan": "p"}, dependency_tag=self.stage.tag)
        self.assertFalse(self.continuity.verify(record, "planning", {"state": 1}, {"context": "ctx"}, {"plan": "p"}, dependency_tag="f" * 64, previous_tag="", sequence=1))

    def test_attack74_hypothesis_cannot_swap_plan_dependency(self):
        plan = self.continuity.attest("planning", {}, {}, {"plan": "A"}, dependency_tag=self.stage.tag)
        hypothesis = self.continuity.attest("hypothesis", {}, {"plan_tag": plan.tag}, {"hypothesis": "A"}, dependency_tag=plan.tag)
        self.assertTrue(self.continuity.verify(hypothesis, "hypothesis", {}, {"plan_tag": plan.tag}, {"hypothesis": "A"}, dependency_tag=plan.tag, previous_tag=plan.tag, sequence=2))
        self.assertFalse(self.continuity.verify(hypothesis, "hypothesis", {}, {"plan_tag": "B"}, {"hypothesis": "A"}, dependency_tag=plan.tag, previous_tag=plan.tag, sequence=2))

    def test_attack75_simulation_binds_hypothesis(self):
        hypothesis = self.continuity.attest("hypothesis", {}, {}, {"hypothesis": "H"}, dependency_tag=self.stage.tag)
        simulation = self.continuity.attest("simulation", {}, {"hypothesis_tag": hypothesis.tag}, {"feasible": True}, dependency_tag=hypothesis.tag)
        self.assertTrue(self.continuity.verify(simulation, "simulation", {}, {"hypothesis_tag": hypothesis.tag}, {"feasible": True}, dependency_tag=hypothesis.tag, previous_tag=hypothesis.tag, sequence=2))
        self.assertFalse(self.continuity.verify(simulation, "simulation", {}, {"hypothesis_tag": "x" * 64}, {"feasible": True}, dependency_tag=hypothesis.tag, previous_tag=hypothesis.tag, sequence=2))

    def test_attack76_allocation_binds_simulation_and_agent(self):
        simulation = self.continuity.attest("simulation", {}, {}, {"feasible": True}, dependency_tag=self.stage.tag)
        allocation = self.continuity.attest("allocation", {}, {"simulation_tag": simulation.tag}, {"agent_id": "agent-a"}, dependency_tag=simulation.tag)
        self.assertTrue(self.continuity.verify(allocation, "allocation", {}, {"simulation_tag": simulation.tag}, {"agent_id": "agent-a"}, dependency_tag=simulation.tag, previous_tag=simulation.tag, sequence=2))
        self.assertFalse(self.continuity.verify(allocation, "allocation", {}, {"simulation_tag": simulation.tag}, {"agent_id": "agent-b"}, dependency_tag=simulation.tag, previous_tag=simulation.tag, sequence=2))

    def test_attack77_execution_binds_allocation(self):
        allocation = self.continuity.attest("allocation", {}, {}, {"agent_id": "agent-a"}, dependency_tag=self.stage.tag)
        execution = self.continuity.attest("execution", {}, {"allocation_tag": allocation.tag}, {"status": "completed"}, dependency_tag=allocation.tag)
        self.assertTrue(self.continuity.verify(execution, "execution", {}, {"allocation_tag": allocation.tag}, {"status": "completed"}, dependency_tag=allocation.tag, previous_tag=allocation.tag, sequence=2))
        self.assertFalse(self.continuity.verify(execution, "execution", {}, {"allocation_tag": "e" * 64}, {"status": "completed"}, dependency_tag=allocation.tag, previous_tag=allocation.tag, sequence=2))

    def test_attack78_verification_binds_exact_execution_output(self):
        execution = self.continuity.attest("execution", {}, {}, {"output": "trusted"}, dependency_tag=self.stage.tag)
        verification = self.continuity.attest("verification", {}, {"execution_tag": execution.tag}, {"valid": True}, dependency_tag=execution.tag)
        self.assertFalse(self.continuity.verify(verification, "verification", {}, {"execution_tag": execution.tag}, {"valid": False}, dependency_tag=execution.tag, previous_tag=execution.tag, sequence=2))

    def test_attack79_metacognition_binds_verified_evidence(self):
        verification = self.continuity.attest("verification", {}, {}, {"valid": True}, dependency_tag=self.stage.tag)
        meta = self.continuity.attest("metacognition", {}, {"verification_tag": verification.tag}, {"confidence": 0.9}, dependency_tag=verification.tag)
        self.assertTrue(self.continuity.verify(meta, "metacognition", {}, {"verification_tag": verification.tag}, {"confidence": 0.9}, dependency_tag=verification.tag, previous_tag=verification.tag, sequence=2))
        self.assertFalse(self.continuity.verify(meta, "metacognition", {}, {"verification_tag": "z" * 64}, {"confidence": 0.9}, dependency_tag=verification.tag, previous_tag=verification.tag, sequence=2))

    def test_attack80_final_chain_requires_exact_order(self):
        records = (
            self.continuity.attest("context", {}, {}, {"v": 1}, dependency_tag=self.stage.tag),
            self.continuity.attest("planning", {}, {}, {"v": 2}, dependency_tag=self.continuity.records[-1].tag),
            self.continuity.attest("verification", {}, {}, {"v": 3}, dependency_tag=self.continuity.records[-1].tag),
        )
        evidence = (
            ("context", {}, {}, {"v": 1}, self.stage.tag),
            ("planning", {}, {}, {"v": 2}, records[0].tag),
            ("verification", {}, {}, {"v": 3}, records[1].tag),
        )
        self.assertTrue(self.continuity.verify_chain(records, evidence))
        forged = (records[0], records[2], records[1])
        self.assertFalse(self.continuity.verify_chain(forged, evidence))

    def test_malformed_record_fails_closed(self):
        self.assertFalse(self.continuity.verify(object(), "planning", {}, {}, {}, dependency_tag=self.stage.tag, previous_tag="", sequence=1))

    def test_record_is_immutable(self):
        record = self.continuity.attest("planning", {}, {}, {}, dependency_tag=self.stage.tag)
        self.assertIsInstance(record, KernelContinuityRecord)
        with self.assertRaises(Exception):
            record.tag = "x"


if __name__ == "__main__":
    unittest.main()
