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
        def finish(output: str, is_error: bool = False, show: bool = True) -> ToolResult:
            result = ToolResult(call_id=call.id, name=call.name, output=output, is_error=is_error)
            self.audit.record("tool_result", name=call.name, is_error=is_error, output=output[:300])
            if is_error and show:
                print(f"\n[Tool error] {call.name}: {output}")
            return result

        try:
            problem = self.tool_registry.validate(call.name, call.args)
            if problem:
                self.audit.record("validation_failed", name=call.name, args=call.args, reason=problem)
                return finish(f"Validation failed: {problem}", True)

            if self.tool_registry.needs_approval(call.name):
                approved = self.cli_approval(call)
                self.audit.record("approval", name=call.name, args=call.args, approved=approved)
                if not approved:
                    return finish("The user denied this action. Do not retry it; report that it was not done.",
                                True, show=False)

            self.audit.record("tool_call", name=call.name, args=call.args)
            output = self.tool_registry.call(call.name, call.args)

            problem = self.tool_registry.verify(call.name, call.args)
            self.audit.record("verification", name=call.name, passed=problem is None, detail=problem)
            if problem:
                return finish(f"The tool reported success, but verification failed: {problem}. "
                            "The action did NOT take effect.", True)

            return finish(output)

        except Exception as e:
            return finish(f"{type(e).__name__}: {e}", True)