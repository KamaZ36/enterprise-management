import asyncio
from abc import ABC, abstractmethod
from pathlib import Path


class MediaStorage(ABC):
    @abstractmethod
    async def save(self, *, folder: str, filename: str, data: bytes) -> str:
        raise NotImplementedError


class LocalDiskStorage(MediaStorage):
    def __init__(self, root: Path, url_prefix: str) -> None:
        self._root = root
        self._url_prefix = url_prefix.rstrip("/")

    async def save(self, *, folder: str, filename: str, data: bytes) -> str:
        target_dir = self._root / folder
        await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((target_dir / filename).write_bytes, data)

        return f"{self._url_prefix}/{folder}/{filename}"
