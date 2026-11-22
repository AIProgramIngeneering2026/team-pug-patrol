from __future__ import annotations

import html

from ..errors import InvalidInput, UnsupportedFormat
from ..tool import Tool, ToolContext, ToolResult
from ._common import decode_utf8, extension, load

TARGETS = {"txt", "pdf", "docx", "html"}
IMPLEMENTED = {("txt", "txt"), ("txt", "html"), ("md", "txt")}  # источник -> цель


class ConvertFormatTool(Tool):
    name = "convert_format"
    input_schema = {
        "type": "object",
        "required": ["fileId", "targetFormat"],
        "additionalProperties": False,
        "properties": {"fileId": {"type": "string"}, "targetFormat": {"type": "string"}},
    }

    def execute(self, input: dict, context: ToolContext) -> ToolResult:
        target = input["targetFormat"]
        if target not in TARGETS:
            raise InvalidInput("targetFormat", f"targetFormat must be one of {sorted(TARGETS)}")
        stored = load(context.file_storage, input["fileId"], "fileId")
        source = extension(stored.name)
        if (source, target) not in IMPLEMENTED:
            raise UnsupportedFormat(f"conversion {source or '?'} -> {target} is not supported",
                                    field="targetFormat")
        context.check_deadline()
        text = decode_utf8(stored, "fileId")
        if target == "html":
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            body = "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
            payload = f"<!doctype html>\n<meta charset=\"utf-8\">\n{body}\n"
        else:
            payload = text
        base = stored.name.rsplit(".", 1)[0]
        out_id = context.file_storage.put(f"{base}.{target}", payload.encode("utf-8"))
        return ToolResult(out_id, {"format": target})
