from __future__ import annotations

from .errors import UnknownOperation
from .tool import Tool


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise UnknownOperation(f"unknown operation '{name}'") from None

    def names(self) -> list[str]:
        return sorted(self._tools)
