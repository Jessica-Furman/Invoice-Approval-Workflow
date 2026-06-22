"""Storage backend interface + local (mock S3) implementation.

Swap LocalStorage for an S3 implementation in M8 without touching callers.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def put_file(self, src_path: str, key: str | None = None) -> str: ...
    def path_for(self, key: str) -> str: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> bool: ...


class LocalStorage:
    """Stores objects as files under a base directory (stands in for an S3 bucket)."""

    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def put_file(self, src_path: str, key: str | None = None) -> str:
        key = key or Path(src_path).name
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest)
        return key

    def path_for(self, key: str) -> str:
        return str(self.base / key)

    def exists(self, key: str) -> bool:
        return (self.base / key).exists()

    def delete(self, key: str) -> bool:
        """Remove the stored object. Returns True if a file was removed."""
        dest = self.base / key
        if dest.exists():
            dest.unlink()
            return True
        return False
