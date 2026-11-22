"""Контракт Tool (практика 2): name, input_schema, execute(input, context) -> ToolResult."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from .errors import ToolTimeout
from .storage import FileStorage


@dataclass
class ToolResult:
    output_file_id: str | None = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {"data": self.data}
        if self.output_file_id is not None:
            d["output_file_id"] = self.output_file_id
        return d


@dataclass
class ToolContext:
    job_id: str
    file_storage: FileStorage
    logger: logging.Logger
    deadline: float  # по часам clock
    clock: Callable[[], float] = time.monotonic

    def check_deadline(self) -> None:
        if self.clock() >= self.deadline:
            raise ToolTimeout("deadline exceeded")


class Tool(ABC):
    name: str
    input_schema: dict

    @abstractmethod
    def execute(self, input: dict, context: ToolContext) -> ToolResult:
        """Бизнес-проверки параметров — здесь. Состояние Job не трогать."""
