#!/usr/bin/env python3
"""Helper CLI to trigger event-driven Hermes webhook routes with HMAC-SHA256 signing.

Usage examples:
  # 1. Instant Telegram notification (zero LLM cost):
  python3 events/trigger_event.py notify -d '{"title": "Build Complete", "message": "All 42 tests passed in 12s!"}'

  # 2. System alert (filtered by severity, diagnosed by gemma4:e4b):
  python3 events/trigger_event.py system-alert -d '{"severity": "error", "source": "nginx", "message": "Port 8080 already in use", "details": "bind() to 0.0.0.0:8080 failed (48: Address already in use)"}'

  # 3. File drop event (summarized by gemma4:e4b):
  python3 events/trigger_event.py file-drop -d '{"action": "created", "file_path": "/Users/jerry/Documents/antigravity/hermes/hermes-wiki.md"}'
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_PORT = int(os.getenv("WEBHOOK_PORT", "8644"))
DEFAULT_SECRET = os.getenv("WEBHOOK_SECRET", "hermes-local-webhook-secret")


def send_webhook(route: str, payload: dict, port: int = DEFAULT_PORT, secret: str = DEFAULT_SECRET) -> None:
    url = f"http://127.0.0.1:{port}/webhooks/{route}"
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    test_out = os.getenv("WEBHOOK_TEST_OUT", "").strip()
    if test_out:
        with open(test_out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "url": url,
                    "route": route,
                    "signature": f"sha256={signature}",
                    "payload": payload,
                },
                f,
            )
        print(f"[✓] Event '{route}' recorded to {test_out}")
        return

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            print(f"[✓] Event '{route}' accepted (HTTP {resp.status}): {resp_body}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[✗] HTTP {e.code} from {url}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(
            f"[✗] Could not reach Hermes Webhook server at {url} ({e.reason}).\n"
            "    Make sure the gateway is running/restarted: hermes gateway restart",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger a Hermes event-driven webhook route.")
    parser.add_argument("route", help="Route name (e.g., notify, git-commit, system-alert, file-drop)")
    parser.add_argument("-d", "--data", required=True, help="JSON payload string")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Webhook server port (default: 8644)")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Webhook HMAC secret")
    args = parser.parse_args()

    try:
        payload = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON passed to --data: {e}", file=sys.stderr)
        sys.exit(1)

    send_webhook(args.route, payload, port=args.port, secret=args.secret)


if __name__ == "__main__":
    main()
