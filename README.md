<div align="center">

<img src="assets/zero-hawk-mark.svg" alt="Zero Hawk mark" width="116" />

# ZERO HAWK

### Find the right businesses. Understand the opportunity. Make every outreach decision count.

**A local-first prospecting and outreach command centre — built to keep your data on your machine and every important action under your control.**

[Quick start](#-quick-start) · [What it does](#-what-zero-hawk-does) · [Safety](#-human-control-first) · [Roadmap](#-honest-status)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue)
![Runs locally](https://img.shields.io/badge/Runs-local-first-9ACD32)
![Tests](https://img.shields.io/badge/CI-Windows%20%7C%20Ubuntu-222222?logo=githubactions)

</div>

---

## The idea

Zero Hawk helps you move from a target market to an organised, evidence-backed prospect list without handing your entire workflow to a black box.

It can discover businesses from OpenStreetMap, research public websites, record buying signals, organise companies and contacts, prepare AI-assisted drafts, and keep approved outreach in a review-first workflow.

It runs on your own computer. Your local database stays local. Optional AI providers and messaging services are only used when you configure them.

> **Built around one rule: you stay in control.** No campaign is silently launched by the background profiling loop. Email sending requires an explicitly approved draft and the configured checks.

## What Zero Hawk does

| Stage | What happens | Where to look |
| --- | --- | --- |
| **Discover** | Find businesses from free OpenStreetMap / Overpass data around a place you choose | Discover |
| **Research** | Read public business websites and collect source-linked observations | Companies |
| **Spot signals** | Score configurable website indicators such as booking, ordering, HTTPS and hiring pages | Signals |
| **Organise** | Keep companies, contacts, campaigns, notes and activity in a local SQLite database | Companies · Contacts · Campaigns |
| **Train** | Read your own website and create an editable local profile for your product, offer and ideal customer | Train |
| **Draft** | Use a configured local or connected AI provider to prepare outreach drafts | Outbox |
| **Review** | Inspect drafts and explicitly approve or reject them | Outbox |
| **Send** | Send an approved, eligible email through configured SMTP | Outbox |
| **Connect** | Expose a small set of local tools to compatible MCP clients | MCP |

### A look at the workflow

```text
  YOUR PRODUCT / OFFER
          |
          v
  TRAIN YOUR WORKSPACE
          |
          v
  DISCOVER BUSINESSES  ---->  COMPANY REGISTER
          |                         |
          v                         v
  RESEARCH PUBLIC SITES      CONTACTS & CAMPAIGNS
          |                         |
          v                         v
  BUYING-SIGNAL EVIDENCE      AI-ASSISTED DRAFTS
                                    |
                                    v
                              HUMAN REVIEW
                                    |
                           approve explicitly
                                    |
                                    v
                              SMTP SEND
```

Zero Hawk can be used one stage at a time. You do not need to connect an email account to use discovery, research, local records, signals or exports.

## ✨ Highlights

- **Local-first:** FastAPI dashboard with a local SQLite database.
- **Free discovery source:** OpenStreetMap / Overpass and Nominatim; no paid API key required for the default source.
- **Evidence-aware research:** Public-site observations retain source URLs and confidence context.
- **Configurable signals:** Deterministic website checks; no AI call is required for signal profiling.
- **Flexible AI:** Ollama, Claude Code CLI, Codex CLI, and optional hosted API-compatible providers.
- **Human-reviewed email:** SMTP sending is gated by explicit approval, recipient status, suppression checks and an HTTPS unsubscribe base URL.
- **Portable data:** CSV import and export for company and contact records.
- **Compatible tools:** Optional MCP server for supported local AI clients.
- **Windows-friendly:** One-click `run.bat` setup for Windows 10/11.

## 🦅 Quick start

### Requirements

- Windows 10 or 11
- Python **3.11 or newer**
- Git for Windows
- Internet connection for package installation and online discovery

No API key is needed to install or open the dashboard. Ollama or another AI provider is optional.

### 1. Clone the repository

Open **Command Prompt** (CMD), then run each command separately:

```cmd
cd %USERPROFILE%
git clone --branch feat/full-platform-roadmap https://github.com/Nex0raLabs/zero-hawk.git
cd openprospect
```

> The repository is still named `openprospect` on GitHub. The product inside it is now **Zero Hawk**. You can rename the GitHub repository later; GitHub redirects old clone URLs after a repository rename.

### 2. Launch Zero Hawk

```cmd
run.bat
```

The launcher creates a virtual environment, installs the application and its MCP extra, creates a starter `.env` file if needed, then starts the private dashboard.

Open the private URL printed in the terminal. It normally uses:

```text
http://127.0.0.1:5555
```

Keep the private token link to yourself. Press **Ctrl+C** in the terminal to stop the server.

### 3. If the launcher does not work

Run these commands from inside the cloned folder:

```cmd
py -3 --version
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,mcp]"
copy .env.example .env
zero-hawk dashboard
```

If `py -3 --version` reports that Python is missing, install Python 3.11+ from [python.org](https://www.python.org/downloads/windows/) and enable **Add Python to PATH** during setup. Reopen CMD after installation.

## First five minutes

1. Open **Train** and enter your business website to create an editable local product profile.
2. Review the generated profile. Extraction is heuristic; correct anything that is wrong.
3. Open **Signals** and choose the website indicators that matter to your offer.
4. Open **Discover**, enter a city or place, choose a business category and search.
5. Open a saved company to inspect its public website and evidence before deciding whether it is a suitable prospect.

You can add companies manually and import CSV records too. Discovery results depend on OpenStreetMap coverage and are not a complete business directory.

## 🧠 Choose an AI provider

AI is optional. The core local workspace does not require a paid model API.

### Ollama — local model

1. Install [Ollama](https://ollama.com/).
2. Open CMD and download a model, for example:

```cmd
ollama pull llama3.2
```

3. In Zero Hawk **Settings**, select Ollama, or set these values in your private `.env`:

```env
OPENPROSPECT_AI_PROVIDER=ollama
OPENPROSPECT_AI_MODEL=llama3.2
OPENPROSPECT_AI_BASE_URL=http://localhost:11434/v1
```

The model runs on your computer. Performance depends on your hardware and the model you download.

### Claude Code CLI or Codex CLI

Choose a CLI provider in Settings if its command-line tool is already installed and signed in on your computer. Use **Test connection** to check the actual connection. A ChatGPT or Claude browser tab cannot directly call a server running on your PC; use a compatible local agent/MCP client instead.

### Optional hosted providers

Anthropic and OpenAI-compatible endpoints can be configured with their respective API keys. Provider usage may incur charges. Never paste API keys into GitHub, screenshots, issues or chat messages.

## 🔌 Connect a compatible AI client (MCP)

Zero Hawk includes an optional local MCP server. Install the extra:

```cmd
python -m pip install -e ".[mcp]"
```

A compatible desktop/agent client can launch the server using the Python executable inside this checkout. Example configuration:

```json
{
  "mcpServers": {
    "zero-hawk": {
      "command": "C:\\Users\\YOUR_USER\\openprospect\\.venv\\Scripts\\python.exe",
      "args": ["-m", "openprospect.mcp_server"],
      "cwd": "C:\\Users\\YOUR_USER\\openprospect"
    }
  }
}
```

Replace `YOUR_USER` with your Windows account folder. The current MCP tools cover searching saved companies, saving a company and asking the configured AI provider. They do not provide a remote cloud bridge into a browser-only chat.

## 🛡️ Human control first

- The background run command profiles saved companies and records signals; it does **not** run an autonomous send campaign.
- Email delivery is optional and requires SMTP configuration.
- A draft must be explicitly approved before it can be sent.
- The send path checks the app's verified-recipient status, suppression list and HTTPS unsubscribe configuration.
- A verification label is a heuristic status, not proof that a person owns or reads an inbox.
- Public contact details do not automatically mean someone has consented to marketing.
- WhatsApp support is an optional unofficial Baileys sidecar and has not been proven production-ready.

Use a test mailbox and contacts you control before any real sending. Follow the marketing, privacy and anti-spam laws that apply to you and your recipients.

## Commands

The primary command is now `zero-hawk`. The previous `openprospect` command remains as a compatibility alias.

```cmd
zero-hawk dashboard
zero-hawk status
zero-hawk companies
zero-hawk train https://your-company.com
zero-hawk run
zero-hawk mcp
```

## Honest status

Zero Hawk is an active local-first alpha, not a finished autonomous sales platform. The following areas are present only in limited form or still need live integration work:

| Area | Current state |
| --- | --- |
| Dashboard, local records, CSV | Implemented; needs your clean-machine acceptance test |
| OpenStreetMap discovery | Implemented; coverage and results vary by area |
| Website signals and training | Implemented with heuristic extraction; review the output |
| AI provider connections | Provider options exist; test with your own installed provider |
| SMTP sending | Implemented with manual approval gates; live mailbox testing required |
| IMAP | Basic unread-message import; not a complete reply-management system |
| WhatsApp | Optional unofficial sidecar; pairing and production safety not verified |
| Decision-maker enrichment | No complete provider-backed enrichment pipeline |
| Campaign automation | No full discovery-to-send autonomous pipeline |
| Production deployment | Not supported as a public multi-user service; dashboard is loopback-only |

See [REPORT.md](REPORT.md) for the detailed evidence-based QA audit, known blockers and release limitations. Do not interpret a feature's presence in the interface as proof of a complete end-to-end integration.

## Troubleshooting

**'git' is not recognized**  
Install [Git for Windows](https://git-scm.com/download/win), reopen CMD and retry.

**'py' is not recognized**  
Install Python 3.11+ and enable the Python Launcher / PATH option.

**The dashboard command is not recognized**  
Activate the virtual environment from the project folder, then run `python -m pip install -e ".[dev,mcp]"` again.

**Port 5555 is already in use**  
Close the other Zero Hawk process first. If you intentionally need another local port, set `OPENPROSPECT_PORT` in `.env` and restart.

**Discovery returns few businesses**  
OpenStreetMap is community-maintained. Try a broader place/category or add companies manually; results are not guaranteed to be complete.

## Project files and privacy

- `.env` — private provider and mailbox settings; never commit it.
- `.venv/` — local Python environment.
- Local database and app state — stored in your user data folder.
- `REPORT.md` — QA evidence and known limitations.

Do not commit real prospect data, mailbox credentials, WhatsApp session files, API keys or dashboard token files.

## Contributing

Issues and pull requests are welcome. Include reproducible steps and tests for code changes. Never submit real personal data or secrets.

## License

Zero Hawk is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE).
