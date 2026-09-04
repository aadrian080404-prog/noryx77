from dataclasses import dataclass
from time import time

@dataclass(frozen=True)
class AuditEvent:
    event: str
    principal_id: str
    timestamp: float

class AuditLog:
    def __init__(self): self.events = []
    def record(self, event, principal_id):
        if not event or not principal_id: raise ValueError("audit identity required")
        self.events.append(AuditEvent(event, principal_id, time()))
