# Hermes Local AI & Event-Driven Automation Workspace

A local AI assistant and event-driven automation suite powered by **Nous Research Hermes Agent**, running locally on **Ollama (`gemma4:e4b`)** and connected to **Telegram (`@a_a_hermes_bot`)**.

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    subgraph Mobile["Mobile & User Interfaces"]
        TG["Telegram App (@a_a_hermes_bot)"]
        CLI["Terminal CLI / TUI (hermes)"]
        WEB["Web Dashboard (localhost:9119)"]
    end

    subgraph Triggers["Local Event Triggers (./events)"]
        CMD["run_and_notify.sh (Command Wrapper)"]
        GIT["git_post_commit.sh (Git Hook)"]
        MAN["trigger_event.py (Signed HMAC CLI)"]
    end

    subgraph Gateway["Hermes Gateway & Webhook Server (~/.hermes)"]
        WH["Webhook Server (localhost:8644)"]
        FILT["filter_severity.py (Severity Filter)"]
        CORE["Hermes Agent Core (Router & Session Manager)"]
        HOOK["activity_logger (Lifecycle Hook)"]
        LOGS["Audit Log (events.jsonl)"]
    end

    subgraph Inference["Local LLM & Tooling"]
        OLLAMA["Ollama Server (localhost:11434/v1)"]
        GEMMA["Model: gemma4:e4b"]
        SKILLS["82 Bundled Skills (GitHub, Browser, macOS, Docs)"]
    end

    TG <-->|"Long Polling (2-Way Chat)"| CORE
    CLI <-->|"Interactive Sessions"| CORE
    WEB <-->|"WebSocket / HTTP"| CORE

    CMD -->|"Exit 0 (notify) / Exit != 0 (system-alert)"| MAN
    GIT -->|"Commit Metadata & Diff"| MAN
    MAN -->|"POST + HMAC-SHA256"| WH

    WH -->|"Direct Delivery (notify)"| TG
    WH -->|"system-alert"| FILT
    FILT -->|"warning / error / critical"| CORE
    WH -->|"git-commit / file-drop"| CORE

    CORE <-->|"OpenAI-Compatible /v1 API"| OLLAMA
    OLLAMA --- GEMMA
    CORE <-->|"Tool Execution"| SKILLS
    CORE -->|"Agent Replies & Alerts"| TG
    CORE -->|"gateway:startup / session / command"| HOOK
    HOOK -->|"Append JSONL"| LOGS
```

---

## 🔄 Event-Driven Execution Flow

```mermaid
sequenceDiagram
    participant Dev as Developer / Script
    participant Trig as trigger_event.py
    participant WH as Webhook Server (:8644)
    participant Flt as filter_severity.py
    participant Agt as Hermes Agent (gemma4:e4b)
    participant TG as Telegram (@a_a_hermes_bot)

    alt Instant Notification (notify route)
        Dev->>Trig: ./events/run_and_notify.sh (Exit 0)
        Trig->>WH: POST /webhooks/notify (HMAC-SHA256)
        WH->>TG: Direct Push Notification (deliver_only, 0 LLM tokens)
    else System Alert / Error Diagnosis (system-alert route)
        Dev->>Trig: ./events/run_and_notify.sh (Exit != 0)
        Trig->>WH: POST /webhooks/system-alert (HMAC-SHA256)
        WH->>Flt: Pass JSON payload on stdin
        Flt-->>WH: Enrich with severity_badge (or [SILENT] if info/debug)
        WH->>Agt: Prompt with error details
        Agt->>TG: Deliver root-cause diagnosis & fix command
    end
```

---

## 📁 Repository Structure

```text
hermes/
├── readme.md                   # Architecture overview and quickstart guide
├── hermes-wiki.md              # Full reference documentation for Hermes Agent
├── install_hermes_agent.sh     # Installer script for Nous Research Hermes Agent
├── events/
│   ├── trigger_event.py        # HMAC-SHA256 webhook client for port 8644
│   ├── run_and_notify.sh       # Wraps commands: notifies on success, diagnoses on error
│   ├── git_post_commit.sh      # Git post-commit hook for AI commit reviews on Telegram
│   ├── filter_severity.py      # Webhook severity filter (mirrored in ~/.hermes/scripts/)
│   └── activity_logger.py      # Gateway lifecycle hook (mirrored in ~/.hermes/hooks/)
└── tests/
    └── test_events.py          # Unit test suite (10 tests covering all event components)
```

---

## 🚀 Quick Start

### 1. Chat with Hermes (`gemma4:e4b`)
```bash
# Terminal REPL / TUI
hermes
hermes --tui

# Or message @a_a_hermes_bot directly on Telegram
```

### 2. Trigger Event-Driven Actions to Telegram
```bash
# Send an instant push notification to @a_a_hermes_bot:
python3 events/trigger_event.py notify -d '{"title": "Deployment Ready", "message": "v1.2.0 is live"}'

# Run any command and get notified (or AI-diagnosed if it fails):
./events/run_and_notify.sh pytest

# Attach AI commit reviews to any Git repository:
ln -sf /Users/jerry/Documents/antigravity/hermes/events/git_post_commit.sh /path/to/repo/.git/hooks/post-commit
```

### 3. Run Unit Tests
```bash
python3 -m unittest discover -s tests -v
```
