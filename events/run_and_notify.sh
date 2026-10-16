#!/bin/bash
# Run any terminal command and automatically trigger a Telegram event when it finishes.
# - On success (exit 0): sends an instant zero-LLM notification via the 'notify' route.
# - On failure (exit != 0): sends the error output to 'system-alert' so gemma4:e4b
#   diagnoses the failure and messages the fix to @a_a_hermes_bot on Telegram.
#
# Usage:
#   ./events/run_and_notify.sh <command> [args...]

if [ $# -eq 0 ]; then
    echo "Usage: $0 <command> [args...]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CMD_STR="$*"
START_TS=$(date +%s)
TMP_OUT=$(mktemp)

echo "→ Running: $CMD_STR"
"$@" > >(tee "$TMP_OUT") 2> >(tee -a "$TMP_OUT" >&2)
EXIT_CODE=$?
END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))
TAIL_OUT=$(tail -n 25 "$TMP_OUT" | cut -c 1-1200)
rm -f "$TMP_OUT"

if [ $EXIT_CODE -eq 0 ]; then
    PAYLOAD=$(python3 -c 'import json, sys; print(json.dumps({"title": "✅ Command Succeeded (" + sys.argv[2] + "s)", "message": "Command: `" + sys.argv[1] + "`\n\nOutput:\n" + sys.argv[3]}))' "$CMD_STR" "$DURATION" "$TAIL_OUT")
    python3 "$SCRIPT_DIR/trigger_event.py" notify -d "$PAYLOAD"
else
    PAYLOAD=$(python3 -c 'import json, sys; print(json.dumps({"severity": "error", "source": "terminal (" + sys.argv[1] + ")", "message": "Command exited with code " + sys.argv[2] + " after " + sys.argv[3] + "s", "details": sys.argv[4]}))' "$CMD_STR" "$EXIT_CODE" "$DURATION" "$TAIL_OUT")
    python3 "$SCRIPT_DIR/trigger_event.py" system-alert -d "$PAYLOAD"
fi

exit $EXIT_CODE
