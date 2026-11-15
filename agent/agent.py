from dotenv import load_dotenv
from langfuse import get_client
from agent.llm.base import LLMClient
from agent.memory import ConversationMemory
from agent.tools.registry import ToolRegistry
from agent.types import Message, ToolCall, ToolResult
from concurrent.futures import ThreadPoolExecutor
import contextvars


load_dotenv()
langfuse = get_client()

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
        with langfuse.start_as_current_observation(name="user-approval", as_type="span") as span:
            answer = input(f"\n[Approval needed] {call.name} with {call.args}\nApprove? (y/n) > ")
            user_res = answer.strip().lower() in ("y", "yes")
            
            span.update(output=user_res)

            return user_res

    def run(self, user_input: str) -> str:
        self.memory.add(Message(role="user", text=user_input))

        for step in range(1, self.max_steps + 1):
            with langfuse.start_as_current_observation(name=f"agent_step", as_type="span", input={"step": step}) as step_span:
                response = self.client.generate(
                    self.memory.messages(),
                    tool_specs=self.tool_registry.specs(),
                    sys_prompt=self.sys_prompt,
                )
                
                self.memory.add_response(response)

                if not response.tool_calls:
                    if response.text:
                        step_span.update(output={"text": response.text})
                        return response.text

                    answer = 'The model returned an empty response.'
                    step_span.update(output={"text": answer})
                    return answer

                results = []
                all_thread_safe = all(self.tool_registry.is_thread_safe(call.name) for call in response.tool_calls)

                if all_thread_safe and len(response.tool_calls) > 1:
                    # Run concurrently
                    with ThreadPoolExecutor() as executor:
                        futures = [executor.submit(contextvars.copy_context().run, self._execute_with_trace, call) for call in response.tool_calls]
                        results = [f.result() for f in futures]
                else:
                    # Run sequentially
                    results = [self._execute_with_trace(call) for call in response.tool_calls]


                self.memory.add_tool_results(results)
                step_span.update(output={"text": response.text, "results": [{"name": r.name, "output": r.output, "is_error": r.is_error} for r in results]})


        answer = f"Stopped: reached the limit of {self.max_steps} steps without finishing."
        return answer

    def _execute(self, call: ToolCall) -> ToolResult:
        def finish(output: str, is_error: bool = False, show: bool = True) -> ToolResult:
            result = ToolResult(call_id=call.id, name=call.name, output=output, is_error=is_error)
            if is_error and show:
                print(f"\n[Tool error] {call.name}: {output}")

            return result

        try:
            problem = self.tool_registry.validate(call.name, call.args)
            if problem:
                return finish(f"Validation failed: {problem}", True)

            if self.tool_registry.needs_approval(call.name):
                approved = self.cli_approval(call)
                if not approved:
                    return finish("The user denied this action. Do not retry it; report that it was not done.",
                                True, show=False)

            output = self.tool_registry.call(call.name, call.args)

            problem = self.tool_registry.verify(call.name, call.args)
            if problem:
                return finish(f"The tool reported success, but verification failed: {problem}. "
                            "The action did NOT take effect.", True)

            return finish(output)

        except Exception as e:
            return finish(f"{type(e).__name__}: {e}", True)

    def _execute_with_trace(self, call: ToolCall) -> ToolResult:
        with langfuse.start_as_current_observation(
            as_type="tool",
            name=call.name,
            input=call.args
        ) as tool:
            result = self._execute(call)
            tool.update(
                output={"output": result.output, "error": result.is_error},
                level="ERROR" if result.is_error else "DEFAULT",
                status_message=result.output if result.is_error else None,
            )
            return result
