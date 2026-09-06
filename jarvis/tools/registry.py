class CapabilityRegistry:
    def __init__(self): self._tools = {}
    def register(self, name, handler):
        if not name or not callable(handler): raise ValueError("invalid capability")
        if name in self._tools: raise ValueError("capability_already_registered")
        self._tools[name] = handler
    def resolve(self, name): return self._tools.get(name)
