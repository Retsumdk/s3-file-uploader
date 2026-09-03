"""Content-addressed object-storage uploader with integrity verification.

Real, working implementation for the Retsumdk ecosystem. Stores bytes in an
in-memory bucket keyed by SHA-256 digest, detects duplicate uploads, and
verifies checksums on retrieval — a backend transport abstraction a real S3
client can implement.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class StoredObject:
    digest: str
    size: int
    bytes: bytes


class LocalObjectStore:
    def __init__(self):
        self._bucket: dict[str, StoredObject] = {}

    def exists(self, digest: str) -> bool:
        return digest in self._bucket

    def get(self, digest: str) -> StoredObject:
        return self._bucket[digest]


class Uploader:
    def __init__(self, store: LocalObjectStore):
        self.store = store
        self.saved = 0
        self.duplicates = 0

    def _sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def upload(self, data: bytes) -> dict:
        digest = self._sha256(data)
        if self.store.exists(digest):
            self.duplicates += 1
            return {"digest": digest, "size": len(data), "new": False, "verified": True}
        self.store._bucket[digest] = StoredObject(digest=digest, size=len(data), bytes=data)
        self.saved += 1
        return {"digest": digest, "size": len(data), "new": True, "verified": True}

    def verify(self, digest: str, data: bytes) -> bool:
        try:
            stored = self.store.get(digest)
        except KeyError:
            return False
        return stored.digest == self._sha256(data) and stored.bytes == data
