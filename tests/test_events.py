#!/usr/bin/env python3
"""Unit tests for Hermes event-driven scripts, webhook filters, and gateway hooks."""
import asyncio
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
EVENTS_DIR = WORKSPACE_DIR / "events"

sys.path.insert(0, str(EVENTS_DIR))
import activity_logger  # noqa: E402
import trigger_event  # noqa: E402


class _FakeHTTPResponse:
    def __init__(self, status: int = 200, body: bytes = b'{"status": "delivered"}'):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestTriggerEvent(unittest.TestCase):
    """Tests for events/trigger_event.py."""

    def test_send_webhook_signs_hmac_and_posts_payload(self):
        payload = {"title": "Unit Test", "message": "Hello from test"}
        secret = "test-secret-key"
        captured_requests = []

        def fake_urlopen(req, timeout=15):
            captured_requests.append((req, timeout))
            return _FakeHTTPResponse(200, b'{"status": "delivered"}')

        out = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen), mock.patch(
            "sys.stdout", out
        ):
            trigger_event.send_webhook("notify", payload, port=8644, secret=secret)

        self.assertEqual(len(captured_requests), 1)
        req, timeout = captured_requests[0]
        self.assertEqual(timeout, 15)
        self.assertEqual(req.full_url, "http://127.0.0.1:8644/webhooks/notify")
        self.assertEqual(json.loads(req.data.decode("utf-8")), payload)

        expected_sig = hmac.new(
            secret.encode("utf-8"), req.data, hashlib.sha256
        ).hexdigest()
        self.assertEqual(
            req.get_header("X-hub-signature-256"), f"sha256={expected_sig}"
        )
        self.assertIn("Event 'notify' accepted (HTTP 200)", out.getvalue())

    def test_send_webhook_http_error_exits_nonzero(self):
        def fake_urlopen(req, timeout=15):
            raise urllib.error.HTTPError(
                req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"error": "invalid signature"}')
            )

        err = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen), mock.patch(
            "sys.stderr", err
        ):
            with self.assertRaises(SystemExit) as ctx:
                trigger_event.send_webhook(
                    "notify", {"title": "Fail"}, port=8644, secret="bad"
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("HTTP 403", err.getvalue())

    def test_send_webhook_connection_error_exits_nonzero(self):
        def fake_urlopen(req, timeout=15):
            raise urllib.error.URLError("Connection refused")

        err = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen), mock.patch(
            "sys.stderr", err
        ):
            with self.assertRaises(SystemExit) as ctx:
                trigger_event.send_webhook(
                    "notify", {"title": "Unreachable"}, port=8644, secret="sec"
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Could not reach Hermes Webhook server", err.getvalue())

    def test_main_invalid_json_exits_nonzero(self):
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch(
            "sys.argv", ["trigger_event.py", "notify", "-d", "{bad json}"]
        ):
            with self.assertRaises(SystemExit) as ctx:
                trigger_event.main()
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Invalid JSON", err.getvalue())


class TestFilterSeverityScript(unittest.TestCase):
    """Tests for events/filter_severity.py (~/.hermes/scripts/filter_severity.py)."""

    SCRIPT_PATH = EVENTS_DIR / "filter_severity.py"

    def _run_filter(self, stdin_text: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.SCRIPT_PATH)],
            input=stdin_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_ignores_low_severity_events(self):
        for level in ("debug", "info", "ok", "INFO"):
            res = self._run_filter(json.dumps({"severity": level, "message": "noise"}))
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "[SILENT]")

    def test_enriches_warning_error_and_critical_events(self):
        cases = {
            "warning": "⚠️ WARNING",
            "error": "🚨 ERROR",
            "critical": "🔥 CRITICAL",
        }
        for level, badge in cases.items():
            res = self._run_filter(
                json.dumps({"severity": level, "source": "db", "message": "disk full"})
            )
            self.assertEqual(res.returncode, 0)
            output = json.loads(res.stdout)
            self.assertEqual(output["severity_badge"], badge)
            self.assertEqual(output["source"], "db")

    def test_invalid_json_returns_silent(self):
        res = self._run_filter("not-valid-json")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "[SILENT]")


class TestActivityLoggerHook(unittest.TestCase):
    """Tests for events/activity_logger.py (~/.hermes/hooks/activity_logger/handler.py)."""

    def test_handle_writes_jsonl_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_home = Path(tmpdir)
            with mock.patch.object(Path, "home", return_value=tmp_home):
                asyncio.run(
                    activity_logger.handle(
                        "command:new",
                        {
                            "platform": "telegram",
                            "user_id": "1806844062",
                            "chat_id": "1806844062",
                            "session_id": "sess-123",
                        },
                    )
                )

            log_file = tmp_home / ".hermes" / "logs" / "events.jsonl"
            self.assertTrue(log_file.exists())
            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["event"], "command:new")
            self.assertEqual(entry["platform"], "telegram")
            self.assertEqual(entry["user_id"], "1806844062")
            self.assertEqual(entry["session_id"], "sess-123")
            self.assertIn("timestamp", entry)


class TestRunAndNotifyScript(unittest.TestCase):
    """Tests for events/run_and_notify.sh."""

    SCRIPT_PATH = EVENTS_DIR / "run_and_notify.sh"

    def test_successful_command_triggers_notify_route(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            out_path = tf.name
        try:
            env = os.environ.copy()
            env["WEBHOOK_TEST_OUT"] = out_path
            res = subprocess.run(
                ["/bin/bash", str(self.SCRIPT_PATH), "echo", "build_ok"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            recorded = json.loads(Path(out_path).read_text(encoding="utf-8"))
            self.assertEqual(recorded["route"], "notify")
            self.assertIn("Command Succeeded", recorded["payload"]["title"])
            self.assertIn("build_ok", recorded["payload"]["message"])
        finally:
            Path(out_path).unlink(missing_ok=True)

    def test_failed_command_triggers_system_alert_route(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            out_path = tf.name
        try:
            env = os.environ.copy()
            env["WEBHOOK_TEST_OUT"] = out_path
            res = subprocess.run(
                [
                    "/bin/bash",
                    str(self.SCRIPT_PATH),
                    "sh",
                    "-c",
                    "echo 'fatal error' >&2; exit 2",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(res.returncode, 2)
            recorded = json.loads(Path(out_path).read_text(encoding="utf-8"))
            self.assertEqual(recorded["route"], "system-alert")
            self.assertEqual(recorded["payload"]["severity"], "error")
            self.assertIn("fatal error", recorded["payload"]["details"])
        finally:
            Path(out_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
