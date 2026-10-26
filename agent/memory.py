from agent.types import LLMResponse, Message, ToolResult


class ConversationMemory:
    def __init__(self):
        self._messages: list[Message] = []

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def add_response(self, response: LLMResponse) -> None:
        self.add(Message(
            role="assistant",
            text=response.text,
            tool_calls=response.tool_calls,
            provider_data=response.provider_data,
        ))

    def add_tool_results(self, results: list[ToolResult]) -> None:
        self.add(Message(role="tool", tool_results=results))

    def messages(self) -> list[Message]:
        return list(self._messages)