from abc import ABC, abstractmethod

from agent.types import ToolSpec


class ToolProvider(ABC):
    @abstractmethod
    def list_tools(self) -> list[ToolSpec]:
        pass

    @abstractmethod
    def call(self, name, args) -> str:
        pass

    @abstractmethod
    def get_tool(self, name: str) -> ToolSpec:
        pass

    def validate(self, name: str, args: dict) -> str | None:
        return None

    def verify(self, name: str, args: dict) -> str | None:
        return None
