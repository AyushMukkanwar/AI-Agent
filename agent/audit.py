import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: str = "run_log.jsonl"):
        self.path = Path(path)

    def record(self, event: str, **data: Any) -> None:
        entry = {"ts": time.strftime("%H:%M:%S"), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")