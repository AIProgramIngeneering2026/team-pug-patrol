from __future__ import annotations

import re

from ..tool import Tool, ToolContext, ToolResult
from ._common import decode_utf8, load

_WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
_SENTENCE = re.compile(r"[^.!?…]*[^\W_][^.!?…]*(?:[.!?…]+|$)", re.UNICODE)
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


class CalculateStatisticsTool(Tool):
    name = "calculate_statistics"
    input_schema = {
        "type": "object",
        "required": ["textFileId"],
        "additionalProperties": False,
        "properties": {"textFileId": {"type": "string"}},
    }

    def execute(self, input: dict, context: ToolContext) -> ToolResult:
        stored = load(context.file_storage, input["textFileId"], "textFileId")
        text = decode_utf8(stored, "textFileId")
        context.check_deadline()
        paragraphs = [p for p in _PARAGRAPH_SPLIT.split(text) if _WORD.search(p)]
        return ToolResult(None, {
            "characters": len(text),
            "words": len(_WORD.findall(text)),
            "sentences": len(_SENTENCE.findall(text)),
            "paragraphs": len(paragraphs),
        })
