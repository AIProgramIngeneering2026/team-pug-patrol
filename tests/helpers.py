import itertools
import logging
import threading
import time

from core import (Dispatcher, InMemoryFileStorage, InMemoryJobRepository, Job, JobState,
                  Tool, ToolResult, build_default_registry)

logging.getLogger("core.dispatcher").addHandler(logging.NullHandler())


def make_env(registry=None, **kw):
    files, jobs = InMemoryFileStorage(), InMemoryJobRepository()
    registry = registry or build_default_registry()
    return Dispatcher(registry, jobs, files, **kw), jobs, files


def job_in_state(state: JobState) -> Job:
    """Привести новый Job в нужное состояние только разрешёнными переходами."""
    job = Job("extract_text", {"fileId": "x"})
    if state is JobState.REJECTED:
        job.reject({"code": "INVALID_INPUT", "message": "m", "field": "fileId"})
        return job
    if state is JobState.CREATED:
        return job
    job.start()
    if state is JobState.SUCCEEDED:
        job.succeed({"data": {}})
    elif state is JobState.FAILED:
        job.fail({"code": "TOOL_INTERNAL_ERROR", "message": "m"})
    return job


class CountingTool(Tool):
    """Tool для проверки «не выполнился повторно» и «Dispatcher не знает конкретных Tool»."""
    name = "counting"
    input_schema = {"type": "object", "required": [], "properties": {}}

    def __init__(self, delay=0.0):
        self.calls = 0
        self.delay = delay
        self._lock = threading.Lock()

    def execute(self, input, context):
        with self._lock:
            self.calls += 1
        time.sleep(self.delay)
        return ToolResult(None, {"ok": True})


class CrashingTool(Tool):
    name = "crashing"
    input_schema = {"type": "object", "required": [], "properties": {}}

    def execute(self, input, context):
        raise RuntimeError("secret internal detail: /srv/db/password")


class MutatingTool(Tool):
    name = "mutating"
    input_schema = {"type": "object", "required": [], "properties": {}}

    def execute(self, input, context):
        input["injected"] = True
        return ToolResult(None, {})
