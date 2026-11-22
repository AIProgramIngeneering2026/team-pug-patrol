from __future__ import annotations

import re

from ..errors import InvalidInput, UnsupportedFormat
from ..tool import Tool, ToolContext, ToolResult
from ._common import decode_utf8, extension, load

SUPPORTED = {"txt", "md"}  # DOCX/PDF требуют библиотек, в этой версии не поддержаны


class ExtractTextTool(Tool):
    name = "extract_text"
    input_schema = {
        "type": "object",
        "required": ["fileId"],
        "additionalProperties": False,
        "properties": {"fileId": {"type": "string"}, "language": {"type": "string"}},
    }

    def execute(self, input: dict, context: ToolContext) -> ToolResult:
        language = input.get("language")
        if language is not None and not re.fullmatch(r"[a-z]{2,3}", language):
            raise InvalidInput("language", "language must be a 2-3 letter lowercase code")
        stored = load(context.file_storage, input["fileId"], "fileId")
        ext = extension(stored.name)
        if ext not in SUPPORTED:
            raise UnsupportedFormat(f"format '{ext}' is not supported", field="fileId")
        context.check_deadline()
        text = decode_utf8(stored, "fileId").replace("\r\n", "\n").replace("\r", "\n")
        base = stored.name.rsplit(".", 1)[0]
        out_id = context.file_storage.put(f"{base}.txt", text.encode("utf-8"))
        return ToolResult(out_id, {"characters": len(text), "detected_language": None})
