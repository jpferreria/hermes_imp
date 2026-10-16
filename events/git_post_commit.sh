#!/bin/bash
# Git post-commit hook that triggers Hermes Agent (@a_a_hermes_bot) to review
# the latest commit and send a concise summary to Telegram.
#
# To install in any Git repo:
#   ln -sf /Users/jerry/Documents/antigravity/hermes/events/git_post_commit.sh /path/to/repo/.git/hooks/post-commit

REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
AUTHOR=$(git log -1 --pretty=format:'%an' 2>/dev/null || echo "unknown")
MESSAGE=$(git log -1 --pretty=format:'%s' 2>/dev/null || echo "")
DIFF_STAT=$(git show --stat --oneline HEAD 2>/dev/null | tail -n +2 | head -n 30)

PAYLOAD=$(python3 -c 'import json, sys; print(json.dumps({
    "repo": sys.argv[1],
    "branch": sys.argv[2],
    "commit": sys.argv[3],
    "author": sys.argv[4],
    "message": sys.argv[5],
    "diff_stat": sys.argv[6]
}))' "$REPO_NAME" "$BRANCH" "$COMMIT" "$AUTHOR" "$MESSAGE" "$DIFF_STAT")

python3 /Users/jerry/Documents/antigravity/hermes/events/trigger_event.py git-commit -d "$PAYLOAD" >/dev/null 2>&1 &
