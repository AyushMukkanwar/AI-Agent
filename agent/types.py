from dataclasses import dataclass, field
import inspect
from typing import Any, Callable, Literal, TypeAlias, get_origin, get_type_hints

MessageRole: TypeAlias = Literal["user", "assistant", "tool"]

_TYPE_MAP = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object",
}

def schema_from_function(func: Callable[..., Any]) -> dict:
    hints = get_type_hints(func)
    properties: dict[str, dict] = {}
    required: list[str] = []

    for name, param in inspect.signature(func).parameters.items():
        py_type = hints.get(name, str)
        py_type = get_origin(py_type) or py_type   # list[str] becomes list
        properties[name] = {"type": _TYPE_MAP.get(py_type, "string")}
        if param.default is inspect.Parameter.empty:
            required.append(name)                  # no default means required

    return {"type": "object", "properties": properties, "required": required}


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    requires_approval: bool = False

@dataclass
class ToolResult:
    call_id: str
    name: str
    output: str
    is_error: bool = False

@dataclass
class Message:
    role: MessageRole
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    provider_data: Any | None = None

@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall]
    provider_data: Any | None = None