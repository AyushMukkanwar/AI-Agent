from anyio import Path

from agent.agent import Agent
from agent.llm.gemini import GeminiClient
from agent.memory import ConversationMemory
from agent.tools.files import ask_user, make_file_tools
from agent.tools.local import LocalToolProvider
from agent.tools.registry import ToolRegistry

MODEL_ID = 'gemini-3.5-flash-lite'

def func():
    client = GeminiClient(MODEL_ID)

    local_tool_provider = LocalToolProvider()

    WORKSPACE = Path(__file__).parent / "workspace"
    list_files, read_file, append_csv_row = make_file_tools(str(WORKSPACE))

    local_tool_provider.register(list_files)
    local_tool_provider.register(read_file)
    local_tool_provider.register(append_csv_row, requires_approval=True)
    local_tool_provider.register(ask_user)

    tool_registry = ToolRegistry([local_tool_provider])

    memory = ConversationMemory()

    SYS_PROMPT = """You are a careful assistant that completes tasks using the tools provided.

        Rules:
        1. Use tools to find information. Never guess or invent values.
        2. If the request is ambiguous or information is missing, use ask_user instead of assuming.
        3. If a tool returns an error, fix the call and retry once if the mistake is fixable. Otherwise stop and report the exact error.
        4. Finish with a short summary of what you did and the evidence for your answer.
        5. Before writing a record, read the destination file to check whether the entry already exists. If it does, do not add a duplicate; tell the user.
        6. Some actions require human approval and will ask the user automatically. If the user denies an action, do not retry it; report that it was not done.
        7. After any write, read the file back and confirm the new row is present and correct. Report this as evidence.
        8. If data looks inconsistent (for example, two documents sharing the same invoice number but different amounts), tell the user, and use ask_user if it affects which record is correct.
        9. When writing invoice records, use this column order: invoice_number, vendor, invoice_date (YYYY-MM-DD), due_date (YYYY-MM-DD), amount (plain number, no currency symbol or commas). If the file is empty or missing, write this header row first.
        """

    agent  = Agent(client=client, tool_registry=tool_registry, memory=memory, max_steps=10, sys_prompt=SYS_PROMPT)

    print(agent.run('Find the latest invoice from KBC technologies, extract the amount and due date, enter it into our internal system, and tell me once it is done'))


if __name__ == "__main__":
    func()