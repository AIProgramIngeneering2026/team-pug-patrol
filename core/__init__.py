from .dispatcher import Dispatcher
from .job import ALLOWED_TRANSITIONS, Job, JobState
from .registry import Registry
from .storage import InMemoryFileStorage, InMemoryJobRepository
from .tool import Tool, ToolContext, ToolResult
from .tools import CalculateStatisticsTool, ConvertFormatTool, ExtractTextTool


def build_default_registry() -> Registry:
    registry = Registry()
    for tool in (ExtractTextTool(), CalculateStatisticsTool(), ConvertFormatTool()):
        registry.register(tool)
    return registry
