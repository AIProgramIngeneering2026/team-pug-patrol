"""Минимальная проверка структуры параметров по input_schema (без внешних библиотек).

Поддержано: required, additionalProperties=false, type, enum.
Это роль «HTTP-слоя» из контракта: структура, типы, обязательные поля — до выполнения.
"""
from __future__ import annotations

from .errors import InvalidInput

_TYPES = {"string": str, "integer": int, "boolean": bool, "object": dict}


def validate(schema: dict, params) -> None:
    if not isinstance(params, dict):
        raise InvalidInput("$", "params must be an object")
    props = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in params:
            raise InvalidInput(name, f"field '{name}' is required")
    if schema.get("additionalProperties") is False:
        for name in params:
            if name not in props:
                raise InvalidInput(name, f"unknown field '{name}'")
    for name, spec in props.items():
        if name not in params:
            continue
        value = params[name]
        expected = _TYPES[spec["type"]]
        bad = not isinstance(value, expected) or (expected is int and isinstance(value, bool))
        if bad:
            raise InvalidInput(name, f"field '{name}' must be {spec['type']}")
        if "enum" in spec and value not in spec["enum"]:
            raise InvalidInput(name, f"field '{name}' must be one of {spec['enum']}")
