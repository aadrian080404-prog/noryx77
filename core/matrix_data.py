"""Content-addressed immutable object manifests (not a distributed storage engine)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib


def sha256_hex(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("content_must_be_bytes")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ObjectManifest:
    object_id: str
    size_bytes: int
    chunk_hashes: tuple[str, ...]
    format_version: int = 1

    @classmethod
    def from_chunks(cls, chunks: tuple[bytes, ...]) -> "ObjectManifest":
        if not chunks or any(not isinstance(chunk, bytes) for chunk in chunks):
            raise ValueError("nonempty_byte_chunks_required")
        hashes = tuple(sha256_hex(chunk) for chunk in chunks)
        payload = (str(sum(map(len, chunks))) + ":" + ":".join(hashes)).encode("ascii")
        return cls(sha256_hex(payload), sum(map(len, chunks)), hashes)

    def verify_chunks(self, chunks: tuple[bytes, ...]) -> bool:
        if len(chunks) != len(self.chunk_hashes):
            return False
        if any(not isinstance(chunk, bytes) for chunk in chunks):
            return False
        if tuple(sha256_hex(chunk) for chunk in chunks) != self.chunk_hashes:
            return False
        payload = (str(sum(map(len, chunks))) + ":" + ":".join(self.chunk_hashes)).encode("ascii")
        return sum(map(len, chunks)) == self.size_bytes and sha256_hex(payload) == self.object_id
