from agent.llm.base import LLMClient
from agent.memory import ConversationMemory
from agent.tools.registry import ToolRegistry
from agent.types import Message, ToolCall, ToolResult


class Agent:
    def __init__(self, client: LLMClient, tool_registry: ToolRegistry,
                 memory: ConversationMemory, max_steps: int = 10,
                 sys_prompt: str | None = None) -> None:
        self.client = client
        self.tool_registry = tool_registry
        self.memory = memory
        self.max_steps = max_steps
        self.sys_prompt = sys_prompt

    def cli_approval(self, call: ToolCall) -> bool:
        answer = input(f"\n[Approval needed] {call.name} with {call.args}\nApprove? (y/n) > ")
        return answer.strip().lower() in ("y", "yes")

    def run(self, user_input: str) -> str:
        self.memory.add(Message(role="user", text=user_input))

        for step in range(1, self.max_steps + 1):
            response = self.client.generate(
                self.memory.messages(),
                tool_specs=self.tool_registry.specs(),
                sys_prompt=self.sys_prompt,
            )
            self.memory.add_response(response)

            if not response.tool_calls:
                if response.text:
                    return response.text
                return "The model returned an empty response."

            results = [self._execute(call) for call in response.tool_calls]
            self.memory.add_tool_results(results)

        return f"Stopped: reached the limit of {self.max_steps} steps without finishing."

    def _execute(self, call: ToolCall) -> ToolResult:
        try:
            if self.tool_registry.needs_approval(call.name) and not self.cli_approval(call):
                return ToolResult(
                    call_id=call.id,
                    name=call.name,
                    output="The user denied this action. Do not retry it; report that it was not done.",
                    is_error=True,
                )
            
            output = self.tool_registry.call(call.name, call.args)
            return ToolResult(call_id=call.id, name=call.name, output=output)
        
        except Exception as e:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                output=f"{type(e).__name__}: {e}",
                is_error=True,
            )