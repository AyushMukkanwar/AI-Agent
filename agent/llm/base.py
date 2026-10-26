from abc import ABC, abstractmethod
from agent.types import LLMResponse, Message, ToolSpec


class LLMClient(ABC):
    @abstractmethod
    def generate(self, messages: list[Message], tool_specs : list[ToolSpec], sys_prompt: str | None = None) -> LLMResponse:
        pass