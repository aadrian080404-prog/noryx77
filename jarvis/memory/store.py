class MemoryStore:
    def __init__(self, max_items=1000):
        if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1:
            raise ValueError("max_items must be positive")
        self._items = {}
        self.max_items = max_items

    def put(self, key, value):
        if not isinstance(key, str) or not key:
            raise ValueError("key required")
        if key not in self._items and len(self._items) >= self.max_items:
            raise MemoryError("memory_capacity_exceeded")
        self._items[key] = value

    def get(self, key):
        return self._items.get(key)
