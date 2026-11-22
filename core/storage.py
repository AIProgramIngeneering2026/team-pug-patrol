"""Интерфейсы хранения и реализации в памяти. Ядро знает только интерфейсы."""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from .errors import JobNotFound


class FileNotInStorage(KeyError):
    pass


@dataclass(frozen=True)
class StoredFile:
    name: str
    content: bytes


class FileStorage(Protocol):
    def put(self, name: str, content: bytes) -> str: ...
    def get(self, file_id: str) -> StoredFile: ...  # raises FileNotInStorage


class InMemoryFileStorage:
    """put атомарен: файл виден целиком или не виден вовсе."""

    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}
        self._lock = threading.Lock()

    def put(self, name: str, content: bytes) -> str:
        file_id = uuid.uuid4().hex
        stored = StoredFile(name, bytes(content))
        with self._lock:
            self._files[file_id] = stored
        return file_id

    def get(self, file_id: str) -> StoredFile:
        with self._lock:
            try:
                return self._files[file_id]
            except KeyError:
                raise FileNotInStorage(file_id) from None


class JobRepository(Protocol):
    def get(self, job_id: str): ...  # raises JobNotFound
    def get_or_create(self, key: str | None, factory: Callable): ...  # -> (job, created)
    def list_all(self) -> list: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, object] = {}
        self._by_key: dict[str, object] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str):
        with self._lock:
            try:
                return self._jobs[job_id]
            except KeyError:
                raise JobNotFound(f"job {job_id} not found") from None

    def get_or_create(self, key: str | None, factory: Callable):
        """Атомарно: два одновременных submit с одним ключом дают один Job."""
        with self._lock:
            if key is not None and key in self._by_key:
                return self._by_key[key], False
            job = factory()
            self._jobs[job.id] = job
            if key is not None:
                self._by_key[key] = job
            return job, True

    def list_all(self) -> list:
        with self._lock:
            return list(self._jobs.values())
