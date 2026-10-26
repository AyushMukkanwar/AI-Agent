# AI Invoice Agent

A tool-augmented AI agent built with Google Gemini to process invoice documents, resolve ambiguities, validate data, and maintain a database of invoice records with human-in-the-loop safeguards.

---

## Features

- **Gemini Enterprise / Vertex AI Integration**: Uses `google-genai` with tool calling and system prompt enforcement.
- **Human-in-the-Loop Approval**: Destructive/writing actions (`create_invoice_record`) prompt the user for CLI approval before execution.
- **Pre-Execution Validation**: Checks date formats (`YYYY-MM-DD`), ensures positive amounts, and prevents duplicate entries before requesting approval.
- **Post-Execution Verification**: Confirms that records were written to disk, catching silent failures.
- **Prompt-Guided Error Recovery**: When a tool fails, the agent inspects the error message, identifies transient failures (such as 503 unavailable), and decides to retry based on system prompt rules.
- **Audit Logging**: Every action, tool call, approval decision, and response is logged into `run_log.jsonl`.

---

## Prerequisites

1. **Google Cloud Platform (GCP) Project**:
   - A GCP project with the **Gemini Enterprise / Agent Platform API** (or Vertex AI API) enabled.
   - Quota for Gemini models (e.g., `gemini-3.5-flash-lite` or `gemini-2.5-flash`).
2. **Google Cloud Authentication**:
   - Set up Application Default Credentials (ADC) on your machine:
     ```bash
     gcloud auth application-default login
     ```
3. **Python 3.10+**

---

## Setup & Installation

1. **Clone the repository and enter the directory**:
   ```bash
   cd agent
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Set your GCP Project ID and Location in your environment:
   ```bash
   export PROJECT_ID="your-gcp-project-id"       # or GOOGLE_CLOUD_PROJECT
   export LOCATION="global"                      # or GOOGLE_CLOUD_LOCATION (defaults to 'global' if omitted)
   ```

---

## Workspace Setup

By default, the agent operates in a directory named `workspace/` located in the project root.

### Default Workspace Structure:
```text
workspace/
├── invoice_1.txt
├── invoice_2.txt
├── invoice_3.txt
├── inovice_4.txt
├── invoice_5.txt
└── db.csv
```

1. **Create the workspace directory**:
   ```bash
   mkdir -p workspace
   ```
2. **Add invoice files**: Place your invoice text files (e.g. `invoice_1.txt`) inside `workspace/`.
3. **Initialize `db.csv`**:
   Create `db.csv` inside `workspace/`:
   ```bash
   touch workspace/db.csv
   ```
   *(The file can start completely empty; the agent automatically writes the header row `invoice_number,vendor,invoice_date,due_date,amount` upon creating the first record).*

### Custom Workspace Location
You do not have to use the default `workspace/` folder. You can configure any directory on your filesystem to act as the workspace by updating the `WORKSPACE` variable in `main.py`:

```python
# main.py
WORKSPACE = Path(__file__).parent / "workspace"  # <-- Replace with Path("/path/to/your/custom/directory")
```

The file tools enforce a safety check ensuring the agent cannot access files outside of the configured `WORKSPACE` path.

---

## Running the Agent

Start the agent interactively:

```bash
python main.py
```

When prompted:
```text
Enter task: Find the latest invoice for KBC Technologies and enter it into the database.
```

### Demonstration Flags

You can test the agent's resilience and verification hooks using built-in failure simulation flags:

- **Simulate Transient 503 Network Failure (`--inject-failure`)**:
  Simulates a temporary `503 ConnectionError` on the first write attempt. The agent will recognize the transient error, retry once, and complete the write.
  ```bash
  python main.py --inject-failure
  ```

- **Simulate Silent Write Failure (`--inject-silent-failure`)**:
  Simulates a mock write that returns a fake success message without writing to disk. The `verify_invoice` post-hook catches the missing row in `db.csv`, and the agent reports that the action did not take effect.
  ```bash
  python main.py --inject-silent-failure
  ```

---

## Project Structure

```text
├── agent/
│   ├── agent.py          # Core Agent loop, step execution, and approval handling
│   ├── audit.py          # Audit logging to run_log.jsonl
│   ├── memory.py         # Conversation memory buffer
│   ├── types.py          # Dataclasses and schema generator
│   ├── llm/
│   │   ├── base.py       # Abstract LLM Client
│   │   └── gemini.py     # Gemini client implementation (reads PROJECT_ID/LOCATION)
│   └── tools/
│       ├── base.py       # Abstract ToolProvider interface
│       ├── files.py      # File tools (list, read, create_invoice, validate, verify)
│       ├── local.py      # Local tool provider with pre/post hooks
│       └── registry.py   # Tool registry
├── demo_failures.py      # Decorators for failure injection (fail_once, silent_failure)
├── main.py               # Main CLI runner, CLI arguments, and prompt configuration
├── requirements.txt      # Python dependencies
└── workspace/            # Default workspace folder
```
