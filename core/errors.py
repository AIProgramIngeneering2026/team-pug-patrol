"""Единый набор ошибок ядра. Коды совпадают с практикой 2 (job-state.md, tool-contract.md)."""
from __future__ import annotations


class CoreError(Exception):
    code = "CORE_ERROR"
    http_status = 500  # для практики 4: соответствие HTTP-статусу, само ядро HTTP не знает

    def __init__(self, message: str = "", *, field: str | None = None):
        self.message = message or self.code
        self.field = field
        super().__init__(self.message)

    def to_dict(self) -> dict:
        d = {"code": self.code, "message": self.message}
        if self.field is not None:
            d["field"] = self.field
        return d


# --- ошибки Job / Dispatcher / Registry ---------------------------------------------------
class InvalidStateTransition(CoreError):
    code = "INVALID_STATE_TRANSITION"
    http_status = 409


class OperationNotSupported(CoreError):
    code = "OPERATION_NOT_SUPPORTED"
    http_status = 409


class UnknownOperation(CoreError):
    """«Неизвестная операция»: имя не зарегистрировано в Registry."""
    code = "UNKNOWN_OPERATION"
    http_status = 400


class JobNotFound(CoreError):
    code = "JOB_NOT_FOUND"
    http_status = 404


class IdempotencyConflict(CoreError):
    code = "IDEMPOTENCY_KEY_REUSED"
    http_status = 409


# --- типизированные ошибки Tool (единый набор из tool-contract.md) ------------------------
class ToolError(CoreError):
    http_status = 422


class InvalidInput(ToolError):
    """«Неверные параметры»: всегда с указанием поля."""
    code = "INVALID_INPUT"

    def __init__(self, field: str, message: str):
        super().__init__(message, field=field)


class UnsupportedFormat(ToolError):
    code = "UNSUPPORTED_FORMAT"


class FileNotFound(ToolError):
    code = "FILE_NOT_FOUND"


class ToolTimeout(ToolError):
    code = "TOOL_TIMEOUT"
    http_status = 504


class ToolInternalError(ToolError):
    code = "TOOL_INTERNAL_ERROR"
    http_status = 500
