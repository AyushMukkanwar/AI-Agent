import csv
from pathlib import Path


def make_file_tools(root: str):
    base = Path(root).resolve()

    def _safe(path: str) -> Path:
        target = (base / path).resolve()
        if not target.is_relative_to(base):
            raise PermissionError("Access outside the workspace folder is not allowed")
        return target

    def list_files(directory: str = ".") -> list[str]:
        """List the files and folders inside a directory of the workspace."""
        return sorted(
            p.name + ("/" if p.is_dir() else "") for p in _safe(directory).iterdir()
        )

    def read_file(path: str) -> str:
        """Read the text content of a file in the workspace."""
        return _safe(path).read_text(encoding="utf-8")

    def append_csv_row(path: str, row: list[str]) -> str:
        """Append one row of values to a CSV file in the workspace. Creates the file if it does not exist."""
        target = _safe(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        return f"Appended row to {path}"

    return list_files, read_file, append_csv_row


def ask_user(question: str) -> str:
    """Ask the human a question when information is missing, ambiguous, or approval is needed. Returns their answer."""
    return input(f"\n[Agent asks] {question}\n> ")
