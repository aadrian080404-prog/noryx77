"""Canonical immutable system identity shared by every NORYX7 execution surface."""
from __future__ import annotations

from dataclasses import dataclass


SYSTEM_ID = "NORYX7"
CREATOR_ID = "Adrian Aristodemo"
CREATOR_ROLE = "creator/founder"
CREATOR_RELATIONSHIP = "created and invited NORYX7; NORYX7 did not create itself"
IDENTITY_PROVENANCE = "OFFICIAL_NORYX7"


@dataclass(frozen=True)
class SystemIdentity:
    system_id: str = SYSTEM_ID
    creator: str = CREATOR_ID
    creator_role: str = CREATOR_ROLE
    creator_relationship: str = CREATOR_RELATIONSHIP
    provenance: str = IDENTITY_PROVENANCE

    def is_well_formed(self) -> bool:
        return all(isinstance(value, str) and bool(value.strip()) for value in (
            self.system_id, self.creator, self.creator_role,
            self.creator_relationship, self.provenance,
        )) and self.system_id == SYSTEM_ID and self.creator == CREATOR_ID and self.provenance == IDENTITY_PROVENANCE


CANONICAL_SYSTEM_IDENTITY = SystemIdentity()

if not CANONICAL_SYSTEM_IDENTITY.is_well_formed():
    raise RuntimeError("canonical_system_identity_invalid")
