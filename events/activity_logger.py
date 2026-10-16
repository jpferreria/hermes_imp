"""Gateway lifecycle hook that records events to ~/.hermes/logs/events.jsonl."""
import datetime
import json
from pathlib import Path


async def handle(event_type: str, context: dict) -> None:
    log_dir = Path.home() / ".hermes" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "events.jsonl"

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": event_type,
        "platform": context.get("platform", "gateway"),
        "user_id": context.get("user_id", ""),
        "chat_id": context.get("chat_id", ""),
        "session_id": context.get("session_id", ""),
    }

    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
