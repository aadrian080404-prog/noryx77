"""Content-addressed immutable object manifests with optional keyed authentication."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac


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

    def canonical_bytes(self) -> bytes:
        if (not isinstance(self.object_id, str) or len(self.object_id) != 64
                or any(c not in "0123456789abcdef" for c in self.object_id)):
            raise ValueError("invalid_object_id")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("invalid_manifest_size")
        if isinstance(self.format_version, bool) or not isinstance(self.format_version, int) or self.format_version != 1:
            raise ValueError("unsupported_manifest_version")
        if not self.chunk_hashes or any(
            not isinstance(item, str) or len(item) != 64 or any(c not in "0123456789abcdef" for c in item)
            for item in self.chunk_hashes
        ):
            raise ValueError("invalid_chunk_hashes")
        return (str(self.format_version) + ":" + str(self.size_bytes) + ":" + self.object_id
                + ":" + ":".join(self.chunk_hashes)).encode("ascii")

    def authenticate(self, key: bytes) -> str:
        if not isinstance(key, bytes) or len(key) < 16:
            raise ValueError("manifest_authentication_key_too_short")
        return hmac.new(key, self.canonical_bytes(), hashlib.sha256).hexdigest()

    def verify_authentication(self, key: bytes, tag: str) -> bool:
        if not isinstance(tag, str):
            return False
        try:
            expected = self.authenticate(key)
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(expected, tag)

    def verify_chunks(self, chunks: tuple[bytes, ...]) -> bool:
        if len(chunks) != len(self.chunk_hashes) or any(not isinstance(chunk, bytes) for chunk in chunks):
            return False
        if tuple(sha256_hex(chunk) for chunk in chunks) != self.chunk_hashes:
            return False
        payload = (str(sum(map(len, chunks))) + ":" + ":".join(self.chunk_hashes)).encode("ascii")
        return sum(map(len, chunks)) == self.size_bytes and sha256_hex(payload) == self.object_id


def verify_authenticated_object(
    manifest: ObjectManifest,
    chunks: tuple[bytes, ...],
    key: bytes,
    authentication_tag: str,
) -> bool:
    """Accept an object only when both manifest authentication and all chunks verify."""
    if not isinstance(manifest, ObjectManifest):
        return False
    if not manifest.verify_authentication(key, authentication_tag):
        return False
    return manifest.verify_chunks(chunks)
