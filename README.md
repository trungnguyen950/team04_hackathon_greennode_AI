# 🤖 AI Service Desk Assistant

> **AI-powered IT Helpdesk automation** — automatically monitors a Gmail inbox, analyzes incoming IT support requests in Vietnamese, runs them through a Multi-Agent LangGraph workflow, creates/updates tickets on ManageEngine ServiceDesk Plus, and replies with detailed HTML troubleshooting guides.

Built for **AI Hackathon 2026** (MSB Bank, Vietnam). Released under the [MIT License](LICENSE).

---

## ✨ Features

- **📧 Fully automated email pipeline** — polls Gmail via IMAP every 15s, classifies, processes, and replies via SMTP.
- **🧠 Multi-Agent LangGraph workflow** with a Center Router that branches into two subflows:
  - **Subflow A — Incident Management (8 steps):** User Request → Intent → Context → Knowledge → Diagnostic → Recommendation → Ticket → Resolution
  - **Subflow B — Software Install (6 steps):** Software Intent → Context → Prerequisites Check → Ticket → Resolution
- **📚 Excel Knowledge Base** — SOP lookup with IF/THEN diagnostic rules, assigned teams, and resolution actions.
- **🎫 ServiceDesk Plus integration** — creates, updates, and closes tickets via REST API; adds notes with full email content.
- **↩️ Multi-turn conversations** — detects `Re: [SVD-xxx]` subjects, accumulates context across replies, updates existing tickets.
- **✅ Auto-resolve detection** — keywords like "đã giải quyết", "ok rồi" close the ticket automatically.
- **🛡️ Prerequisite checks** — validates Office 365 E3 / MS Teams licenses before approving software installs.
- **⚠️ Non-catalog software** (AutoCAD, Photoshop, etc.) flagged as `PENDING_IT_EVALUATION`.
- **💬 Web Chat Simulator** (`/chat`) — test the full AI pipeline without sending real emails.
- **🖥️ Live Log Console** (`/logs`) — real-time WebSocket log streaming with category filters and bot controls.
- **🎨 Professional HTML email replies** — ticket cards, diagnostic boxes, step-by-step SOP guidance, ServiceDesk links.
- **🐳 Docker-ready** — single `Dockerfile`, exposes port 8080.

---

## 🏗️ Architecture

```
┌──────────────┐    IMAP poll     ┌──────────────────────────────────────────────┐
│  Gmail Inbox │ ───────────────► │  main_email_bot.py  (polling daemon, 15s)    │
│  (support)   │ ◄─────────────── │  └─► email_ai_processor.process_incoming_email│
└──────────────┘    SMTP reply    └──────────────────────────────────────────────┘
                                          │
                                          ▼
                          ┌─────────────────────────────────┐
                          │   LangGraph Main Workflow        │
                          │   step1_user_request             │
                          │        │                        │
                          │   center_router  (LLM classify)  │
                          │     ┌────┴────┐                 │
                          │     ▼         ▼                 │
                          │  Subflow A  Subflow B            │
                          │  (Incident) (Software Install)   │
                          │  8 steps    6 steps              │
                          │     └────┬────┘                 │
                          │          ▼                       │
                          │   Resolution (HTML email)        │
                          └─────────────────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
          ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
          │  Knowledge Base │   │  ServiceDesk    │   │  Local DB       │
          │  (Excel .xlsx)  │   │  Plus REST API  │   │  tickets_db.json│
          └─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Project Structure

```
AI-ServiceDesk-Assistant/
├── main_email_bot.py            # Email polling daemon (IMAP + SMTP)
├── email_ai_processor.py        # LangGraph orchestrator + fallback
├── shared_langchain_components.py # LLM client (OpenAI-compatible)
├── config.py                    # Env-based configuration
├── web_app.py                   # FastAPI: home, logs, bot controls, WebSocket
├── web_chat_app.py              # FastAPI: web chat simulator router
├── agent_8_steps/
│   ├── workflow.py              # LangGraph definition (main + 2 subflows)
│   ├── state.py                 # TypedDict shared state
│   ├── kb_engine.py             # Excel KB loader + keyword matching
│   ├── ticket_system.py         # Ticket lifecycle (incident + service request)
│   ├── prerequisite_checker.py  # License eligibility checks
│   └── nodes/                   # 15 step nodes (center_router, step1-8, step2b-6b)
├── utils/
│   ├── gmail_utils.py           # Gmail IMAP/SMTP + Google API client
│   ├── svd_utils.py             # ServiceDesk Plus REST API client
│   ├── excel_utils.py           # openpyxl wrapper
│   ├── log_manager.py           # WebSocket log streaming + stdout tee
│   ├── string_utils.py          # HTML strip, reply/history extraction
│   ├── date_utils.py            # Date/time helpers
│   ├── dict_utils.py            # Dict manipulation + flatten keys
│   ├── regex_utils.py           # Regex helpers
│   └── type_utils.py            # Type detection
├── templates/
│   ├── home.html                # Landing page with scenarios
│   ├── log_viewer.html          # Live terminal-style console
│   └── chat_simulator.html      # Web chat UI
├── data/                        # Runtime data (gitignored — personal)
├── logs/                        # App logs (gitignored)
├── Optimized_IT_KnowledgeBase_v1.2.xlsx  # KB (gitignored — proprietary)
├── templates/                   # Jinja2 HTML templates
├── requirements.txt
├── Dockerfile
├── .env.example                 # Config template (safe to commit)
├── .gitignore
├── LICENSE                      # MIT
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- A **Gmail account** with a [Google App Password](https://myaccount.google.com/apppasswords) (16 chars)
- An **OpenAI-compatible LLM API key** (default endpoint: VNG Cloud GreenNode)
- (Optional) **ManageEngine ServiceDesk Plus** instance with REST API access
- (Required for KB matching) An **Excel Knowledge Base** file (see [Knowledge Base Format](#knowledge-base-format))

### 1. Clone & install

```bash
git clone https://github.com/trungnguyen950/team04_hackathon_greennode_AI.git
cd team04_hackathon_greennode_AI

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp env.example .env
```

Edit `.env` and fill in your values:

```ini
GMAIL_EMAIL=your-servicedesk-bot@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
OPENAI_API_KEY=your-api-key-here
POLL_INTERVAL_SECONDS=15
PORT=8080
```

### 3. Add your Knowledge Base

Place your Excel KB file in the project root:

```
Optimized_IT_KnowledgeBase_v1.2.xlsx
```

See [Knowledge Base Format](#knowledge-base-format) for the required schema.

### 4. Run

**Option A — Email bot only (CLI daemon):**

```bash
python main_email_bot.py                    # continuous polling
python main_email_bot.py --once             # single scan, then exit
python main_email_bot.py --dry-run          # AI replies to console, no SMTP
python main_email_bot.py --interval 30      # custom poll interval
```

**Option B — Web app (FastAPI + auto-starts bot):**

```bash
python web_app.py
```

Then open:
- **Home** → http://localhost:8080
- **Live Console** → http://localhost:8080/logs
- **Web Chat** → http://localhost:8080/chat

**Option C — Docker:**

```bash
docker build -t ai-servicedesk .
docker run -p 8080:8080 --env-file .env -v $(pwd)/Optimized_IT_KnowledgeBase_v1.2.xlsx:/app/Optimized_IT_KnowledgeBase_v1.2.xlsx ai-servicedesk
```

---

## 📊 Knowledge Base Format

The Excel file (`Optimized_IT_KnowledgeBase_v1.2.xlsx`) must contain two sheets:

### Sheet 1: `IncidentReport`

| Column | Description |
|---|---|
| `KB_ID` | Unique knowledge base ID (e.g. `NET-03.1`) |
| `Category` | Issue category (e.g. `Network / Physical`) |
| `Intent_Name` | Intent label (e.g. `Physical Connectivity Issue`) |
| `User_Utterances` | Pipe-separated example phrases |
| `Required_Context` | Info to collect (e.g. `UserID, Device, Issue Details`) |
| `Diagnostic_Condition` | IF rule (symptom pattern) |
| `Root_Cause` | THEN rule (likely cause) |
| `Resolution_Action` | SOP steps |
| `Assigned_Team` | Responsible team (e.g. `Network Team`) |
| `Sample_Scenario` | Example scenario |

### Sheet 2: `ServiceRequest`

| Column | Description |
|---|---|
| `KB_ID` | Unique ID (e.g. `SOF_01.02`) |
| `Category` | Software category |
| `Software_Name` | Canonical name (e.g. `MS Office 365`) |
| `Work_Purposes` | Pipe-separated use cases |
| `Required_Context` | Info to collect (e.g. `Phòng ban, IP máy in`) |
| `Prerequisites` | Rule name (e.g. `check_office_365_E3_license`) or `No` |
| `Assigned_Team` | Responsible team |

> **Note:** The KB file is gitignored by default because it typically contains organization-specific SOP data. Share it out-of-band or provide a sanitized example in your fork.

---

## 🔧 Configuration Reference

All config is env-based (see `config.py` and `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `GMAIL_EMAIL` | — | Gmail account to monitor |
| `GMAIL_APP_PASSWORD` | — | Google App Password (16 chars) |
| `OPENAI_API_KEY` | — | LLM API key |
| `POLL_INTERVAL_SECONDS` | `15` | Seconds between inbox scans |
| `PORT` | `8080` | Web server port |

ServiceDesk Plus settings are hardcoded in `utils/svd_utils.py` (`SVD_URL`, `AUTHTOKEN`) — override by editing that file or patching `svd_utils.load_config(...)`.

---

## 🌐 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Home page (scenarios + guide) |
| `GET` | `/chat` | Web chat simulator |
| `GET` | `/logs` | Live log console |
| `GET` | `/health` | Health check |
| `GET` | `/api/status` | System status (bot state, ticket count) |
| `GET` | `/api/logs` | Log history (`?limit=200&category=error`) |
| `POST` | `/api/logs/clear` | Clear logs |
| `GET` | `/api/logs/download` | Download `app.log` |
| `POST` | `/api/bot/trigger` | Trigger one scan cycle |
| `POST` | `/api/bot/start` | Start auto-polling |
| `POST` | `/api/bot/stop` | Stop auto-polling |
| `GET` | `/api/chat/history` | Chat session history |
| `POST` | `/api/chat/message` | Send chat message (runs AI pipeline) |
| `POST` | `/api/chat/reset` | Reset chat session |
| `WS` | `/ws/logs` | Real-time log stream |

---

## 🧪 How It Works (End-to-End Example)

1. **User sends email** to `your-servicedesk-bot@gmail.com`:
   > *"Sáng nay tôi mở máy nhưng không có mạng. Nhờ IT hỗ trợ kiểm tra cấu hình giúp tôi."*

2. **`main_email_bot.py`** picks up the unread email via IMAP.

3. **`email_ai_processor.py`** invokes the LangGraph workflow:
   - **Step 1 — User Request:** Cleans body, extracts reply history.
   - **Center Router:** LLM classifies as `incident` (not `software_install`).
   - **Step 2 — Intent:** Category `Network / Physical`, intent `Physical Connectivity Issue`, priority `HIGH`.
   - **Step 3 — Context:** Extracts UserID, device env, error status.
   - **Step 4 — Knowledge:** Matches KB record `NET-03.1` (root cause + SOP).
   - **Step 5 — Diagnostic:** Confirms root cause, `AUTO_RESOLVE=NO`.
   - **Step 6 — Recommendation:** LLM generates step-by-step Vietnamese guidance.
   - **Step 7 — Ticket:** Creates `SVD-xxx` on ServiceDesk Plus, saves to `tickets_db.json`.
   - **Step 8 — Resolution:** Builds HTML email, saves to `resolutions_history.json`.

4. **SMTP reply** sent to user with HTML ticket card + diagnostic + SOP steps + ServiceDesk link.

5. **User replies** `Re: [SVD-xxx] ...` → system detects existing ticket, **updates** it (no new ticket), accumulates context.

6. **User says** *"tôi đã có mạng rồi, cảm ơn"* → auto-detected as resolved → ticket **closed** on ServiceDesk Plus.

---

## 🛠️ Development

### Run tests

```bash
pytest                          # if tests are added
```

### Lint

```bash
ruff check .                    # if ruff is installed
```

### Project conventions

- **Language**: Python 3.11+, type hints encouraged.
- **Comments**: Vietnamese inline comments are common throughout the codebase.
- **LLM prompts**: All in Vietnamese, expecting structured `KEY: value` responses.
- **State**: LangGraph `TypedDict` (`agent_8_steps/state.py`) shared across all nodes.
- **No tests currently included** — consider adding `tests/` in your fork.

---

## ⚠️ Security Notes

- **Never commit `.env`** — it contains your Gmail App Password and API keys. The included `.gitignore` blocks it.
- **Never commit the Excel KB** if it contains proprietary SOP data — gitignored by default.
- **Never commit `data/`** — contains real tickets with personal email addresses — gitignored.
- **ServiceDesk Plus credentials** in `utils/svd_utils.py` (`AUTHTOKEN`) are hardcoded — move to env vars for production use.
- **Hardcoded guest credentials** (`guest` / `Guest@123`) appear in email HTML templates for ticket URL access — remove or replace for production.
- Use a dedicated Gmail account for the bot, not a personal one.
- Restrict the Google App Password to only Gmail (no other scopes).

---

## 📦 Deployment

### Docker

```bash
docker build -t ai-servicedesk .
docker run -d \
  -p 8080:8080 \
  --env-file .env \
  -v "$PWD/Optimized_IT_KnowledgeBase_v1.2.xlsx:/app/Optimized_IT_KnowledgeBase_v1.2.xlsx:ro" \
  -v "$PWD/data:/app/data" \
  -v "$PWD/logs:/app/logs" \
  --name ai-servicedesk \
  ai-servicedesk
```

### Production checklist

- [ ] Set all env vars via secret manager (not plaintext `.env`)
- [ ] Move `SVD_AUTH_TOKEN` / `SVD_URL` to env vars
- [ ] Remove hardcoded `guest`/`Guest@123` from templates
- [ ] Use HTTPS + reverse proxy (nginx/caddy) in front of FastAPI
- [ ] Set up log rotation for `logs/app.log`
- [ ] Monitor Gmail API quotas / IMAP rate limits
- [ ] Back up `data/tickets_db.json` regularly

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure no secrets or proprietary KB data are included in your PR.

---

## 📄 License

[MIT](LICENSE) — © 2026 AI Service Desk Assistant Contributors.

This project uses third-party libraries (FastAPI, LangChain, LangGraph, openpyxl, etc.) under their respective licenses.

---

## 🙏 Acknowledgements

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — Multi-agent state machine
- **[LangChain](https://github.com/langchain-ai/langchain)** — LLM orchestration
- **[FastAPI](https://fastapi.tiangolo.com/)** — Web framework
- **[openpyxl](https://openpyxl.readthedocs.io/)** — Excel I/O
- **[ManageEngine ServiceDesk Plus](https://www.manageengine.com/products/service-desk/)** — Ticketing platform
- Built for **AI Hackathon 2026**
