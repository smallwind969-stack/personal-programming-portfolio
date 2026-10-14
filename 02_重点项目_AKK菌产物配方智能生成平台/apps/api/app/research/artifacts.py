from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path

import joblib


@dataclass(frozen=True)
class StoredModelArtifact:
    fingerprint: str
    uri: str
    localPath: str
    metadataPath: str


class ContentAddressedModelArtifactStore:
    """Trusted internal joblib store. Loading is intentionally not exposed over API."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, model_bundle, metadata: dict) -> StoredModelArtifact:
        buffer = BytesIO(); joblib.dump(model_bundle, buffer, protocol=5, compress=3)
        payload = buffer.getvalue(); digest = sha256(payload).hexdigest()
        model_path = self.root / f"{digest}.joblib"; metadata_path = self.root / f"{digest}.json"
        if not model_path.exists(): self._atomic_write(model_path, payload)
        manifest = {**metadata, "artifactFingerprint": f"sha256:{digest}", "artifactFile": model_path.name,
                    "securityWarning": "Trusted internal artifact only; joblib files must never be loaded from unverified sources."}
        canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        if not metadata_path.exists(): self._atomic_write(metadata_path, canonical)
        return StoredModelArtifact(f"sha256:{digest}", f"artifact://models/{digest}", str(model_path), str(metadata_path))

    def verify(self, fingerprint: str) -> bool:
        digest = fingerprint.removeprefix("sha256:")
        path = self.root / f"{digest}.joblib"
        if not path.exists() or sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("model artifact integrity verification failed")
        return True

    def load_verified(self, fingerprint: str, uri: str):
        """Load only an internally registered content-addressed artifact after digest verification."""
        digest = fingerprint.removeprefix("sha256:")
        if uri != f"artifact://models/{digest}":
            raise ValueError("model artifact URI does not match its fingerprint")
        self.verify(fingerprint)
        return joblib.load(self.root / f"{digest}.joblib")

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        temporary.write_bytes(payload); os.replace(temporary, path)
