import inspect
import json
from typing import Any, Callable

from agent.tools.base import ToolProvider
from agent.types import ToolSpec, schema_from_function


class LocalToolProvider(ToolProvider):
    def __init__(self):
        self._specs: dict[str, ToolSpec] = {}
        self._funcs: dict[str, Callable[..., Any]] = {}
        self._validators: dict[str, Callable[[dict], str | None]] = {}
        self._verifiers: dict[str, Callable[[dict], str | None]] = {}

    def register(self, func: Callable[..., Any],name: str | None = None, description: str | None = None, parameters: dict | None = None, requires_approval: bool = False,  validate=None, verify=None) -> None:
        name = name or func.__name__
        description = description or inspect.getdoc(func) or ""
        parameters = parameters or schema_from_function(func)
        
        if name in self._funcs:
            raise ValueError(f"Tool '{name}' is already registered")
        self._specs[name] = ToolSpec(name=name, description=description,
                                     parameters=parameters, requires_approval=requires_approval)
        self._funcs[name] = func

        if validate:
            self._validators[name] = validate
        if verify:
            self._verifiers[name] = verify

    def list_tools(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def call(self, name: str, args: dict) -> str:
        func = self._funcs.get(name)
        if func is None:
            raise KeyError(f"Unknown tool: {name}")

        result = func(**args)
        if isinstance(result, str):
            return result
        return json.dumps(result, default=str)

    def get_tool(self, name: str) -> ToolSpec:
        return self._specs[name]

    def validate(self, name: str, args: dict) -> str | None:
        fn = self._validators.get(name)
        return fn(args) if fn else None

    def verify(self, name: str, args: dict) -> str | None:
        fn = self._verifiers.get(name)
        return fn(args) if fn else None