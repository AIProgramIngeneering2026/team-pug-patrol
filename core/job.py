"""Job: состояния и проверка переходов. Правило живёт здесь, а не в вызывающем коде."""
from __future__ import annotations

import copy
import threading
import uuid
from enum import Enum
from types import MappingProxyType

from .errors import InvalidStateTransition, OperationNotSupported


class JobState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


# Ровно переходы из диаграммы job-state.md. Всё, чего здесь нет, запрещено.
ALLOWED_TRANSITIONS = MappingProxyType({
    JobState.CREATED: frozenset({JobState.RUNNING, JobState.REJECTED}),
    JobState.RUNNING: frozenset({JobState.SUCCEEDED, JobState.FAILED}),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.REJECTED: frozenset(),
})
TERMINAL_STATES = frozenset(s for s, nxt in ALLOWED_TRANSITIONS.items() if not nxt)


class Job:
    def __init__(self, operation: str, params: dict, idempotency_key: str | None = None,
                 job_id: str | None = None):
        self.id = job_id or uuid.uuid4().hex
        self.operation = operation
        self.idempotency_key = idempotency_key
        self._params = copy.deepcopy(params)
        self._state = JobState.CREATED
        self._result: dict | None = None
        self._error: dict | None = None
        self._history: list[tuple[JobState | None, JobState]] = [(None, JobState.CREATED)]
        self._lock = threading.Lock()

    # Только чтение: состояние меняется исключительно через transition_to.
    @property
    def state(self) -> JobState:
        return self._state

    @property
    def params(self) -> dict:
        return copy.deepcopy(self._params)

    @property
    def result(self) -> dict | None:
        return copy.deepcopy(self._result)

    @property
    def error(self) -> dict | None:
        return copy.deepcopy(self._error)

    @property
    def history(self) -> tuple:
        return tuple(self._history)

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    def transition_to(self, target: JobState, *, result: dict | None = None,
                      error: dict | None = None) -> None:
        """Единственная точка смены состояния. Проверка и смена атомарны (под замком)."""
        target = JobState(target)
        with self._lock:
            if target not in ALLOWED_TRANSITIONS[self._state]:
                raise InvalidStateTransition(
                    f"transition {self._state.value} -> {target.value} is not allowed")
            self._history.append((self._state, target))
            self._state = target
            if target is JobState.SUCCEEDED:
                self._result = copy.deepcopy(result)
            elif target in (JobState.FAILED, JobState.REJECTED):
                self._error = copy.deepcopy(error)

    def start(self) -> None:
        self.transition_to(JobState.RUNNING)

    def succeed(self, result: dict) -> None:
        self.transition_to(JobState.SUCCEEDED, result=result)

    def fail(self, error: dict) -> None:
        self.transition_to(JobState.FAILED, error=error)

    def reject(self, error: dict) -> None:
        self.transition_to(JobState.REJECTED, error=error)

    def cancel(self) -> None:
        """Отмена в текущей версии не поддерживается; состояние не меняется."""
        raise OperationNotSupported("job cancellation is not supported")
