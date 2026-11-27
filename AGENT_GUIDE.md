# ZERO HAWK — Connect your AI agent

ZERO HAWK can expose its local workspace to an MCP-compatible AI client. This is how an assistant such as Claude Desktop can inspect your saved prospects, research websites, check mailbox readiness, prepare drafts and read activity from a conversation.

The MCP server runs on your computer and talks to the same local database as the dashboard. It does not upload your local database to ZERO HAWK.

## 1. Install the MCP extra

Open Command Prompt in your ZERO HAWK folder:

```cmd
.venv\\Scripts\\activate
python -m pip install -e ".[mcp]"
```

## 2. Add ZERO HAWK to Claude Desktop

Open Claude Desktop's developer configuration file. On Windows it is normally:

`%APPDATA%\\Claude\\claude_desktop_config.json`

Add this configuration, replacing `YOUR_WINDOWS_USER` with your Windows account folder:

```json
{
  "mcpServers": {
    "zero-hawk": {
      "command": "C:\\Users\\YOUR_WINDOWS_USER\\zero-hawk\\.venv\\Scripts\\python.exe",
      "args": ["-m", "openprospect.mcp_server"],
      "cwd": "C:\\Users\\YOUR_WINDOWS_USER\\zero-hawk"
    }
  }
}
```

Save the file completely and restart Claude Desktop. Look for ZERO HAWK in the connected tools list. If it does not appear, check the path and confirm that the `mcp` extra installed successfully.

## 3. What your connected AI can do

The current MCP toolset allows an AI client to:

- Search saved companies and read company, contact and signal details.
- Discover businesses from OpenStreetMap and save new prospects locally.
- Read public company websites and save evidence-based website signals.
- Read your saved company/product/offer profile.
- List contacts, campaigns, drafts and recent activity.
- Create campaign containers without starting them.
- Prepare personalised email drafts and save them to the Outbox.
- Check SMTP/IMAP configuration, inspect DNS records, view Autopilot state and check the sending pause switch.
- Sync unread email from your configured IMAP inbox into local conversations.
- Ask the AI provider configured in ZERO HAWK for writing or analysis.

## 4. Try this prompt

```text
Use ZERO HAWK to set up outbound research for my business.
First read my company and offer profile. Then find businesses in Nairobi
in the category I specify. Save the prospects, research their public
websites, identify evidence-backed signals, and show me a shortlist.
Do not invent decision-makers or email addresses. Do not send anything.
```

You can also ask it to inspect mailbox readiness, check your domain's SPF/DMARC/MX records, prepare an email draft for a saved contact, or summarise recent activity.

## 5. Human approval and limits

The MCP server intentionally does **not** expose tools to approve drafts, send emails, send WhatsApp messages, disable the global send pause, or turn Autopilot on. Those actions stay in the ZERO HAWK dashboard and remain under your control.

A configured SMTP/IMAP connection is not proof that a live login succeeded. A DNS result is not a guarantee of inbox placement. Website signals are heuristic observations, not proof of buying intent. The AI must report unavailable integrations honestly.

Email warmup is not performed by these MCP tools. ZERO HAWK must not simulate warmup activity or claim that a mailbox is warming when no genuine warmup provider is connected.

## Compatibility note

This is a local stdio MCP server. It is designed for MCP clients that can launch a local process, such as Claude Desktop. A cloud-only chat client cannot reach a server running only on your PC; that requires a separately secured remote MCP deployment. Do not expose the local dashboard or MCP process directly to the public internet.
