"""Dispatcher: выбирает Tool в Registry, ведёт Job по состояниям.

Конкретных Tool не знает — только контракт. Новый Tool = register() в Registry.
"""
from __future__ import annotations

import copy
import logging
import time
from typing import Callable

from . import schema
from .errors import CoreError, IdempotencyConflict, InvalidInput
from .job import Job, JobState
from .registry import Registry
from .storage import FileStorage, JobRepository
from .tool import ToolContext, ToolResult

SERVICE_RESTARTED = {"code": "SERVICE_RESTARTED",
                     "message": "job was interrupted by a service restart"}


class Dispatcher:
    def __init__(self, registry: Registry, jobs: JobRepository, files: FileStorage,
                 logger: logging.Logger | None = None, timeout_seconds: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self._registry = registry
        self._jobs = jobs
        self._files = files
        self._log = logger or logging.getLogger("core.dispatcher")
        self._timeout = timeout_seconds
        self._clock = clock

    # --- приём запроса: created -> rejected при неверных параметрах --------------------------
    def submit(self, operation: str, params: dict, idempotency_key: str | None = None) -> Job:
        tool = self._registry.get(operation)  # UnknownOperation: Job не создаётся
        job, created = self._jobs.get_or_create(
            idempotency_key, lambda: Job(operation, params, idempotency_key))
        if not created:
            if job.operation != operation or job.params != params:
                raise IdempotencyConflict("idempotency key was used with a different request")
            return job
        try:
            schema.validate(tool.input_schema, params)
        except InvalidInput as e:
            job.reject(e.to_dict())
        return job

    # --- выполнение: created -> running -> succeeded | failed --------------------------------
    def run(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        job.start()  # атомарно; повторный/параллельный запуск -> InvalidStateTransition
        try:
            tool = self._registry.get(job.operation)
            context = ToolContext(job.id, self._files, self._log,
                                  self._clock() + self._timeout, self._clock)
            result = tool.execute(copy.deepcopy(job.params), context)
            if not isinstance(result, ToolResult):
                raise TypeError("tool returned a non-ToolResult value")
        except CoreError as e:  # типизированные ошибки Tool
            job.fail(e.to_dict())
        except Exception:  # падение Tool: детали в лог, клиенту — общий код
            self._log.exception("tool %s crashed in job %s", job.operation, job.id)
            job.fail({"code": "TOOL_INTERNAL_ERROR", "message": "internal tool error"})
        else:
            job.succeed(result.to_dict())
        return job

    def execute(self, operation: str, params: dict, idempotency_key: str | None = None) -> Job:
        """submit + run. Уже существующий или отклонённый Job повторно не запускается."""
        job = self.submit(operation, params, idempotency_key)
        if job.state is JobState.CREATED:
            self.run(job.id)
        return job

    def cancel(self, job_id: str) -> None:
        self._jobs.get(job_id).cancel()  # всегда OPERATION_NOT_SUPPORTED, состояние не меняется

    # --- З2: вызывать один раз при старте сервиса, до приёма запросов ------------------------
    def recover_interrupted(self) -> list[Job]:
        recovered = []
        for job in self._jobs.list_all():
            if job.state is JobState.RUNNING:
                job.fail(dict(SERVICE_RESTARTED))
                recovered.append(job)
        return recovered
