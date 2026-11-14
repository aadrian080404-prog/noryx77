import unittest

from .context import ContextManager


class ContextBoundaryTests(unittest.TestCase):
    def test_build_isolates_nested_mutation(self):
        source = {"nested": {"items": [1, 2]}}
        snapshot = ContextManager().build("task-1", source, ("task-1",))
        source["nested"]["items"].append(3)
        self.assertEqual(snapshot.values["nested"]["items"], [1, 2])

    def test_build_rejects_malformed_identity_and_sources(self):
        manager = ContextManager()
        with self.assertRaises(ValueError):
            manager.build("", {}, ())
        with self.assertRaises(ValueError):
            manager.build("task-1", {}, ("",))
        with self.assertRaises(ValueError):
            manager.build("task-1", [], ())
        with self.assertRaises(ValueError):
            manager.build("task-1", {}, [])

    def test_versions_are_monotonic_per_task(self):
        manager = ContextManager()
        first = manager.build("task-1", {}, ())
        second = manager.build("task-1", {}, ())
        other = manager.build("task-2", {}, ())
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(other.version, 1)


if __name__ == "__main__":
    unittest.main()
