import threading
import unittest
from dataclasses import replace

from .memory import MemoryItem, MemoryStore


class Memory181To190Tests(unittest.TestCase):
    def test_attack181_concurrent_puts_cannot_exceed_capacity(self):
        store = MemoryStore(max_items=1)
        barrier = threading.Barrier(3)
        outcomes = []

        def writer(memory_id):
            barrier.wait()
            try:
                store.put(MemoryItem(memory_id, "payload"))
                outcomes.append("ok")
            except MemoryError:
                outcomes.append("capacity")

        first = threading.Thread(target=writer, args=("m1",))
        second = threading.Thread(target=writer, args=("m2",))
        first.start(); second.start(); barrier.wait()
        first.join(); second.join()

        self.assertEqual(len(store), 1)
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(outcomes.count("capacity"), 1)
        self.assertEqual(len(store.list()), 1)

    def test_attack182_corrupted_memory_cannot_be_deleted_as_a_bypass(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", "good"))
        store._items["m1"] = replace(store._items["m1"], content="tampered")

        with self.assertRaisesRegex(MemoryError, "memory_integrity_failure"):
            store.delete("m1")
        self.assertEqual(len(store), 1)

    def test_attack183_authenticated_delete_still_removes_exact_item(self):
        store = MemoryStore()
        store.put(MemoryItem("m1", "good"))
        store.put(MemoryItem("m2", "keep"))

        self.assertTrue(store.delete("m1"))
        self.assertIsNone(store.get("m1"))
        self.assertEqual(store.get("m2").content, "keep")
        self.assertEqual(len(store), 1)

    def test_attack184_concurrent_replacement_preserves_capacity(self):
        store = MemoryStore(max_items=1)
        store.put(MemoryItem("m1", "original"))
        barrier = threading.Barrier(3)
        failures = []

        def replace_item(content):
            barrier.wait()
            try:
                store.put(MemoryItem("m1", content))
            except Exception as exc:
                failures.append(exc)

        first = threading.Thread(target=replace_item, args=("one",))
        second = threading.Thread(target=replace_item, args=("two",))
        first.start(); second.start(); barrier.wait()
        first.join(); second.join()

        self.assertEqual(failures, [])
        self.assertEqual(len(store), 1)
        item = store.get("m1")
        self.assertIn(item.content, {"one", "two"})

    def test_attack185_failed_integrity_check_does_not_change_other_entries(self):
        store = MemoryStore(max_items=2)
        store.put(MemoryItem("m1", "good"))
        store.put(MemoryItem("m2", "keep"))
        store._items["m1"] = replace(store._items["m1"], content="tampered")

        with self.assertRaises(MemoryError):
            store.delete("m1")
        self.assertEqual(store.get("m2").content, "keep")
        self.assertEqual(len(store), 2)


if __name__ == "__main__":
    unittest.main()
