import unittest

from .finch import EventGraph, MachineInspiredAnalyzer, Observation


class MachineInspiredTests(unittest.TestCase):
    def obs(self, oid="o1", subject="system", severity=0.2, signal="normal"):
        return Observation(oid, 1.0, "test", subject, signal, severity)

    def test_relevance_is_deterministic_and_bounded(self):
        analyzer = MachineInspiredAnalyzer()
        items = (self.obs("b", severity=0.8, signal="database alert"), self.obs("a", severity=0.2))
        first = analyzer.rank_relevance(items, keywords=("database",))
        second = analyzer.rank_relevance(items, keywords=("database",))
        self.assertEqual(first, second)
        self.assertGreaterEqual(first[0].score, 0.0)
        self.assertLessEqual(first[0].score, 1.0)
        self.assertEqual(first[0].observation_id, "b")

    def test_anomaly_detection_is_fail_closed_on_empty_input(self):
        self.assertEqual(MachineInspiredAnalyzer().detect_anomalies(()), ())

    def test_forecast_groups_by_subject_and_is_bounded(self):
        analyzer = MachineInspiredAnalyzer()
        result = analyzer.forecast((self.obs("a", "x", 0.9), self.obs("b", "x", 0.7), self.obs("c", "y", 0.1)))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].subject, "x")
        self.assertEqual(result[0].evidence, ("a", "b"))
        self.assertLessEqual(result[0].likelihood, 1.0)

    def test_graph_digest_is_deterministic(self):
        graph = EventGraph(max_events=4)
        graph.add(self.obs("o1"), related_to=("device", "network"))
        graph.add(self.obs("o2"), related_to=("device",))
        snapshot = graph.snapshot()
        self.assertEqual(snapshot.digest, graph.snapshot().digest)
        self.assertIn(("o1", "device"), snapshot.edges)

    def test_graph_capacity_and_neighbor_bounds(self):
        graph = EventGraph(max_events=1, max_neighbors=1)
        graph.add(self.obs("o1"))
        with self.assertRaises(OverflowError):
            graph.add(self.obs("o2"))
        graph = EventGraph(max_events=2, max_neighbors=1)
        with self.assertRaises(ValueError):
            graph.add(self.obs("o1"), related_to=("a", "b"))

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.obs(severity=1.1)
        with self.assertRaises(ValueError):
            MachineInspiredAnalyzer().forecast((self.obs(),), horizon=0)
        with self.assertRaises(ValueError):
            MachineInspiredAnalyzer().analyze((self.obs(),) * 4097)


if __name__ == "__main__":
    unittest.main()
