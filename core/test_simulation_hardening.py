import unittest

from .contracts import TaskSpec
from .reasoning import Hypothesis, InternalSimulator


class SimulationHardeningTests(unittest.TestCase):
    def setUp(self):
        self.simulator = InternalSimulator()
        self.task = TaskSpec("sim", "analysis", "answer", {}, constraints={"max_steps": 2})

    def hypothesis(self, suffix="0", task_id="sim", statement="answer", basis=None):
        return Hypothesis(
            f"{task_id}:h{suffix}",
            task_id,
            statement,
            (basis or f"{task_id}:{suffix}",),
            1,
            (task_id,),
        )

    def test_accepts_well_formed_bounded_hypothesis(self):
        simulations = self.simulator.simulate(self.task, (self.hypothesis(),))
        self.assertEqual(simulations[0].reason, "feasible")
        self.assertTrue(self.simulator.verify(simulations).valid)

    def test_rejects_step_budget_exceeded(self):
        hypotheses = (self.hypothesis("0"), self.hypothesis("1"), self.hypothesis("2"))
        simulations = self.simulator.simulate(self.task, hypotheses)
        self.assertEqual(len(simulations), 1)
        self.assertFalse(simulations[0].feasible)
        self.assertEqual(simulations[0].reason, "step_budget_exceeded")

    def test_rejects_invalid_step_budget_constraint(self):
        task = TaskSpec("sim", "analysis", "answer", {}, constraints={"max_steps": 0})
        simulations = self.simulator.simulate(task, (self.hypothesis(),))
        self.assertEqual(simulations[0].reason, "invalid_max_steps_constraint")

    def test_rejects_context_binding_mismatch(self):
        hypotheses = (self.hypothesis("0"), self.hypothesis("1"))
        tampered = Hypothesis("sim:h1", "sim", "answer", ("sim:1",), 2, ("sim",))
        simulations = self.simulator.simulate(self.task, (hypotheses[0], tampered))
        self.assertEqual(simulations[0].reason, "context_binding_mismatch")

    def test_rejects_foreign_hypothesis_task(self):
        simulations = self.simulator.simulate(self.task, (self.hypothesis(task_id="foreign"),))
        self.assertEqual(simulations[0].reason, "hypothesis_task_mismatch")

    def test_rejects_invalid_basis_identity(self):
        simulations = self.simulator.simulate(self.task, (self.hypothesis(basis="foreign:0"),))
        self.assertEqual(simulations[0].reason, "hypothesis_basis_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
