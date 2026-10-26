import csv
from datetime import datetime
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

    def create_invoice_record(invoice_number: str, vendor: str, invoice_date: str,
                          due_date: str, amount: float) -> str:
        """Create an invoice record in the internal system (db.csv)."""
        for label, value in (("invoice_date", invoice_date), ("due_date", due_date)):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"{label} '{value}' is invalid. Expected format YYYY-MM-DD.")

        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        target = _safe("db.csv")
        new_file = not target.exists() or target.stat().st_size == 0

        if not new_file:
            content = target.read_bytes()
            if content and not content.endswith(b"\n"):
                with target.open("ab") as f:
                    f.write(b"\n")

        with target.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["invoice_number", "vendor", "invoice_date", "due_date", "amount"])
            writer.writerow([invoice_number, vendor, invoice_date, due_date, amount])

        return f"Created record {invoice_number} in db.csv"

    def _read_invoice_rows() -> list[dict]:
        target = _safe("db.csv")
        if not target.exists():
            return []
        with target.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def validate_invoice(args: dict) -> str | None:
        for label in ("invoice_date", "due_date"):
            try:
                datetime.strptime(str(args.get(label, "")), "%Y-%m-%d")
            except ValueError:
                return f"{label} must be YYYY-MM-DD, got '{args.get(label)}'"
        try:
            if float(args.get("amount", 0)) <= 0:
                return "amount must be greater than zero"
        except (TypeError, ValueError):
            return "amount must be a number"
        for row in _read_invoice_rows():
            if (row.get("invoice_number") == str(args.get("invoice_number"))
                    and row.get("invoice_date") == args.get("invoice_date")):
                return (f"A record for {args.get('invoice_number')} dated "
                        f"{args.get('invoice_date')} already exists")
        return None

    def verify_invoice(args: dict) -> str | None:
        for row in _read_invoice_rows():
            if (row.get("invoice_number") == str(args.get("invoice_number"))
                    and row.get("invoice_date") == args.get("invoice_date")
                    and row.get("due_date") == args.get("due_date")
                    and float(row.get("amount", 0)) == float(args.get("amount", 0))):
                return None
        return "the record was not found in db.csv after writing"

    return (list_files, read_file, append_csv_row, create_invoice_record,
        validate_invoice, verify_invoice)


def ask_user(question: str) -> str:
    """Ask the human a question when information is missing, ambiguous, or approval is needed. Returns their answer."""
    return input(f"\n[Agent asks] {question}\n> ")
