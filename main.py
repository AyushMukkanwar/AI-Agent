import argparse
from pathlib import Path

from agent.agent import Agent
from agent.llm.gemini import GeminiClient
from agent.memory import ConversationMemory
from agent.tools.files import ask_user, make_file_tools
from agent.tools.local import LocalToolProvider
from agent.tools.registry import ToolRegistry
from demo_failures import fail_once

MODEL_ID = 'gemini-3.5-flash-lite'


def func():
    parser = argparse.ArgumentParser(description="Run the AI agent.")
    parser.add_argument(
        "--inject-failure",
        action="store_true",
        help="Inject a temporary failure into invoice creation for demonstration.",
    )
    parser.add_argument(
        "--inject-silent-failure",
        action="store_true",
        help="Inject a silent failure into invoice creation for demonstration.",
    )
    args = parser.parse_args()

    client = GeminiClient(MODEL_ID)

    local_tool_provider = LocalToolProvider()

    WORKSPACE = Path(__file__).parent / "workspace"
    list_files, read_file, _, create_invoice_record, validate_invoice, verify_invoice = make_file_tools(str(WORKSPACE))

    if args.inject_failure:
        create_invoice_record = fail_once(create_invoice_record)
    if args.inject_silent_failure:
        from demo_failures import silent_failure
        create_invoice_record = silent_failure(create_invoice_record)

    local_tool_provider.register(list_files)
    local_tool_provider.register(read_file)
    local_tool_provider.register(
        create_invoice_record,
        requires_approval=True,
        validate=validate_invoice,
        verify=verify_invoice,
    )
    local_tool_provider.register(ask_user)

    tool_registry = ToolRegistry([local_tool_provider])

    memory = ConversationMemory()

    SYS_PROMPT = """You are a careful assistant that completes tasks using the tools provided.

        Rules:
        1. Use tools to find information. Always use the exact filenames returned by list_files; never infer or guess filenames.
        2. If the request is ambiguous, information is missing, or the vendor name does not exactly match the documents (including abbreviations like 'KBC Tech' for 'KBC Technologies'), use ask_user to clarify before taking action or writing.
        3. If a tool returns an error, fix the call and retry once if the mistake is fixable. If an action fails verification or says the action did NOT take effect, stop and report the exact error; do not attempt to circumvent it.
        4. Finish with a short summary of what you did and the evidence for your answer.
        5. Before writing a record, read the destination file to check whether the invoice_number already exists. If it does, do not add a duplicate regardless of whether the requested amount or format differs; tell the user.
        6. Some actions require human approval and will ask the user automatically. If the user denies an action, do not retry it; report that it was not done.
        7. After any write, read the file back and confirm the new row is present and correct. Report this as evidence.
        8. If data looks inconsistent (for example, two documents sharing the same invoice number but different amounts or dates), asking for the "latest" does NOT resolve it. You MUST tell the user and use ask_user to clarify which document is correct before writing anything.
        9. When writing invoice records, use this column order: invoice_number, vendor, invoice_date (YYYY-MM-DD), due_date (YYYY-MM-DD), amount (plain number, no currency symbol or commas). If the file is empty or missing, write this header row first.
        10. The amount to record is the Total Amount Due (including tax) unless the user says otherwise. State this in your summary.
        11. If the vendor name in the request does not exactly match the documents (for example a typo or abbreviation), confirm the match with ask_user before writing anything.
        12. Ask the user at most one clarifying question per ambiguity. If they decline or say no, stop and report what you found; do not ask again.
        13. If an error says it is temporary, retry the same call once. If it fails again, stop and report the exact error.
        14. In your final summary, mention any tool errors you hit and how you recovered from them.
        15. Only use create_invoice_record to enter invoice records.
        """

    agent = Agent(client=client, tool_registry=tool_registry, memory=memory, max_steps=15, sys_prompt=SYS_PROMPT)

    user_input = input("Enter task: ")
    print(agent.run(user_input))


if __name__ == "__main__":
    func()
