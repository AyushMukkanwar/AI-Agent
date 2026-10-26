from agent.tools.base import ToolProvider
from agent.types import ToolSpec


class ToolRegistry:
    def __init__(self, providers: list[ToolProvider]):
        self._providers = providers
        self._routes: dict[str, ToolProvider] = {}

        for provider in providers:
            for spec in provider.list_tools():
                if spec.name in self._routes:
                    raise ValueError(f"Duplicate tool name: {spec.name}")
                self._routes[spec.name] = provider

    def specs(self) -> list[ToolSpec]:
        return [spec for p in self._providers for spec in p.list_tools()]

    def call(self, name: str, args: dict) -> str:
        provider = self._routes.get(name)
        if provider is None:
            raise KeyError(f"Unknown tool: {name}")
        return provider.call(name, args)

    def needs_approval(self, name: str) -> bool:
        provider = self._routes.get(name)
        if provider is None:
            return False
        return provider.get_tool(name).requires_approval