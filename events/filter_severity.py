#!/usr/bin/env python3
"""Filter and enrich system-alert webhook payloads.

Ignores low-priority ("debug", "info") events and passes through "warning",
"error", or "critical" events for Hermes to analyze and deliver to Telegram.
"""
import json
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    print("[SILENT]")
    raise SystemExit(0)

severity = str(payload.get("severity", "warning")).lower().strip()
if severity in {"debug", "info", "ok"}:
    print("[SILENT]")
    raise SystemExit(0)

payload["severity_badge"] = {
    "warning": "⚠️ WARNING",
    "error": "🚨 ERROR",
    "critical": "🔥 CRITICAL",
}.get(severity, f"🔔 {severity.upper()}")

print(json.dumps(payload))
