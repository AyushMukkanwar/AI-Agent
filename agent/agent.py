from agent.audit import AuditLog
from agent.llm.base import LLMClient
from agent.memory import ConversationMemory
from agent.tools.registry import ToolRegistry
from agent.types import Message, ToolCall, ToolResult


class Agent:
    def __init__(self, client: LLMClient, tool_registry: ToolRegistry,
                 memory: ConversationMemory, max_steps: int = 10,
                 sys_prompt: str | None = None, audit: AuditLog | None = None) -> None:
        self.client = client
        self.tool_registry = tool_registry
        self.memory = memory
        self.max_steps = max_steps
        self.sys_prompt = sys_prompt
        self.audit = audit or AuditLog()

    def cli_approval(self, call: ToolCall) -> bool:
        answer = input(f"\n[Approval needed] {call.name} with {call.args}\nApprove? (y/n) > ")
        return answer.strip().lower() in ("y", "yes")

    def run(self, user_input: str) -> str:
        self.audit.record("run_started", task=user_input)
        self.memory.add(Message(role="user", text=user_input))

        for step in range(1, self.max_steps + 1):
            response = self.client.generate(
                self.memory.messages(),
                tool_specs=self.tool_registry.specs(),
                sys_prompt=self.sys_prompt,
            )
            
            self.audit.record("llm_response", step=step, text=response.text,
                  tool_calls=[c.name for c in response.tool_calls])
            
            self.memory.add_response(response)

            if not response.tool_calls:
                if response.text:
                    self.audit.record("run_finished", answer=response.text)
                    return response.text

                answer = 'The model returned an empty response.'
                self.audit.record("run_finished", answer=answer)
                return answer

            results = [self._execute(call) for call in response.tool_calls]
            self.memory.add_tool_results(results)

        answer = f"Stopped: reached the limit of {self.max_steps} steps without finishing."
        self.audit.record("run_finished", answer=answer)
        return answer

    def _execute(self, call: ToolCall) -> ToolResult:
        self.audit.record("tool_call", name=call.name, args=call.args)
        try:
            if self.tool_registry.needs_approval(call.name):
                approved = self.cli_approval(call)
                self.audit.record("approval", name=call.name, args=call.args, approved=approved)

                if not approved:
                    self.audit.record("approval_denied", name=call.name)
                    return ToolResult(
                        call_id=call.id,
                        name=call.name,
                        output="The user denied this action. Do not retry it; report that it was not done.",
                        is_error=True,
                    )
            
            output = self.tool_registry.call(call.name, call.args)
            result = ToolResult(call_id=call.id, name=call.name, output=output)
            self.audit.record("tool_result", name=call.name, is_error=result.is_error, output=result.output[:300])
            return result
        
        except Exception as e:
            print(f"\n[Tool error] {call.name}: {type(e).__name__}: {e}")
            result = ToolResult(
                call_id=call.id,
                name=call.name,
                output=f"{type(e).__name__}: {e}",
                is_error=True,
            )
            self.audit.record("tool_result", name=call.name, is_error=result.is_error, output=result.output[:300])
            return result