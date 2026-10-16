# Hermes Agent Wiki & Documentation

Welcome to the local documentation for **Hermes Agent**, an open-source, self-improving AI assistant by Nous Research. This documentation outlines the directory structure, configurations, and core commands for running and customizing Hermes.

---

## 📂 File & Directory Structure

Hermes keeps its core assets and state files in your home directory:

*   **Config:** `~/.hermes/config.yaml`
    Main configuration file for adjusting model parameters, display interfaces, tools, and behavior.
*   **API Keys / Environment:** `~/.hermes/.env`
    Stores provider API keys (OpenRouter, Anthropic, OpenAI, etc.).
*   **Personality Customization:** `~/.hermes/SOUL.md`
    Edit this markdown file to customize the agent's persona, system instructions, and demeanor.
*   **Source Code & Environment:** `~/.hermes/hermes-agent`
    Contains the installed virtual environment (`venv`) and raw sources.
*   **Sessions & History:** `~/.hermes/sessions/`
    Local database directory for past conversational sessions.
*   **Logs:** `~/.hermes/logs/`
    Contains debugging logs (`agent.log` and `errors.log`).
*   **Bundled Skills:** `~/.hermes/skills/`
    Preloaded capabilities and tools (e.g. GitHub integrations, system scripts, Apple automation tools).

---

## 🚀 Core Commands

| Command | Description |
| :--- | :--- |
| `hermes` | Launch interactive chat (classic REPL or modern TUI) |
| `hermes setup` | Start the interactive setup wizard to configure APIs & models |
| `hermes config` | Print current configuration values |
| `hermes config edit` | Open `config.yaml` directly in your default terminal editor |
| `hermes dashboard` | Launch the Web UI dashboard on `http://localhost:9119` |
| `hermes logs -f` | Stream and follow debugging logs in real-time |
| `hermes update` | Update the Hermes executable and dependency repositories |
| `hermes sessions list` | Display history of recent sessions |

---

## 🛠️ Advanced Usage

### Running the TUI vs. Classic REPL
Hermes provides two command-line interfaces:
*   **Classic REPL (CLI):** Focused, standard terminal input.
    ```bash
    hermes --cli
    ```
*   **Text User Interface (TUI):** A richer terminal interface.
    ```bash
    hermes --tui
    ```

### Resuming Sessions
Resume your most recent workspace session:
```bash
hermes -c
```
Or resume a specific session by ID:
```bash
hermes --resume <session_id>
```

### Gateway & Background Crons
Deploy the Hermes gateway background service (for messaging integration and automated cron tasks):
```bash
hermes gateway install
```

---

## 🧠 Local Ollama Configuration (`gemma4:e4b`)

Hermes is configured to use your local Ollama instance (`gemma4:e4b`) via the OpenAI-compatible `/v1` endpoint in `~/.hermes/config.yaml`:

```yaml
model:
  default: gemma4:e4b
  provider: custom
  base_url: http://localhost:11434/v1
```

### CLI Commands to Update Model Config
```bash
hermes config set model.provider custom
hermes config set model.base_url http://localhost:11434/v1
hermes config set model.default gemma4:e4b
```

### Context Length Recommendation
Because Hermes injects tool schemas and system prompts, start Ollama with a larger context window (e.g., 32k tokens):
```bash
OLLAMA_CONTEXT_LENGTH=32768 ollama serve
```

---

## 📱 Mobile Connectivity (Telegram: `@a_a_hermes_bot`)

Hermes is connected to Telegram via **`@a_a_hermes_bot`**.

### Useful Telegram & Gateway Commands
* **In Telegram chat:**
  * `/help` — Show available bot commands
  * `/new` — Start a fresh conversation session
  * `/sethome` — Set the current Telegram chat as the default delivery channel for scheduled tasks (crons)
  * `/stop` — Interrupt an active agent turn
* **In your terminal:**
  * `hermes gateway` — Run the gateway in the foreground
  * `hermes gateway install` — Install/enable the gateway background service
  * `hermes pairing list` — View paired/authorized users
  * `hermes pairing approve telegram <CODE>` — Approve a new user's pairing code

---

## ⚡ Event-Driven Actions (`@a_a_hermes_bot`)

Hermes runs an event-driven Webhook Server on `http://127.0.0.1:8644` alongside Gateway Lifecycle Hooks (`~/.hermes/hooks/`).

### 1. Configured Webhook Routes (`~/.hermes/config.yaml`)
| Route | Endpoint | Mode | Description |
| :--- | :--- | :--- | :--- |
| **`notify`** | `/webhooks/notify` | Direct (`deliver_only`) | Instant zero-LLM Telegram push notification (`{title}`, `{message}`). |
| **`git-commit`** | `/webhooks/git-commit` | AI Agent (`gemma4:e4b`) | Reviews Git commits (`{repo}`, `{branch}`, `{commit}`, `{diff_stat}`) and sends a summary to Telegram. |
| **`system-alert`** | `/webhooks/system-alert` | Filtered + AI Agent | Runs `~/.hermes/scripts/filter_severity.py` (ignores `info`/`debug`) and diagnoses `warning`/`error`/`critical` alerts on Telegram. |
| **`file-drop`** | `/webhooks/file-drop` | AI Agent (`gemma4:e4b`) | Summarizes or extracts action items when a file event (`{action}`, `{file_path}`) triggers. |

### 2. Local Event Trigger Scripts (`./events/`)
* **Trigger any event manually:**
  ```bash
  python3 events/trigger_event.py notify -d '{"title": "Build Done", "message": "Finished in 8s"}'
  ```
* **Wrap any terminal command (auto-notify on success, AI-diagnose on error):**
  ```bash
  ./events/run_and_notify.sh <command> [args...]
  ```
* **Auto-review commits in any Git repository:**
  ```bash
  ln -sf /Users/jerry/Documents/antigravity/hermes/events/git_post_commit.sh /path/to/repo/.git/hooks/post-commit
  ```

### 3. Gateway Lifecycle Hook (`~/.hermes/hooks/activity_logger/`)
Automatically logs `gateway:startup`, `session:start`, `session:reset`, and `command:*` events to `~/.hermes/logs/events.jsonl`.
