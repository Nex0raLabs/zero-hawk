"""MCP tools that let a connected AI agent work with the local Zero Hawk workspace.

The agent may research, organise and prepare work. Sending, approving drafts,
changing safety controls and enabling autopilot are deliberately not exposed.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .db import (
    add_campaign, add_company, add_draft, connect, find_company_duplicate, is_suppressed,
    list_activity, list_campaigns, list_companies, list_contacts, list_drafts,
    save_company_observations,
)
from .ai import ask_ai
from .discovery import discover_osm
from .profiling import profile_website
from .training import load_training

mcp = FastMCP("Zero Hawk")


def _company(company_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    if not row:
        raise ValueError(f"Company {company_id} was not found.")
    return dict(row)


@mcp.tool()
def search_companies(limit: int = 50, query: str = "") -> list[dict]:
    """Search companies already saved in Zero Hawk by name, industry, location or website."""
    rows = list_companies(max(1, min(int(limit), 200)))
    needle = query.strip().lower()
    if needle:
        rows = [row for row in rows if needle in " ".join(
            str(row.get(key, "")) for key in ("name", "industry", "location", "website", "notes")
        ).lower()]
    return rows


@mcp.tool()
def get_company(company_id: int) -> dict:
    """Read one saved company's details and recorded website observations."""
    company = _company(company_id)
    with connect() as conn:
        observations = [dict(row) for row in conn.execute(
            "SELECT * FROM observations WHERE company_id=? ORDER BY id DESC LIMIT 100",
            (company_id,),
        )]
        contacts = [dict(row) for row in conn.execute(
            "SELECT * FROM contacts WHERE company_id=? ORDER BY id DESC LIMIT 100",
            (company_id,),
        )]
    return {"company": company, "observations": observations, "contacts": contacts}


@mcp.tool()
def discover_businesses(city_or_place: str, category: str = "any business", limit: int = 30) -> dict:
    """Find businesses using free OpenStreetMap data and save new, non-duplicate prospects locally."""
    results = discover_osm(city_or_place, category, max(1, min(int(limit), 100)))
    saved, skipped = [], 0
    for item in results:
        duplicate = find_company_duplicate(item.get("website", ""), item.get("phone", ""))
        if duplicate:
            skipped += 1
            continue
        ident = add_company(
            item["name"], item.get("website", ""), item.get("category", category),
            item.get("address", "") or city_or_place, "", "openstreetmap",
            item.get("source_url", ""), item.get("phone", ""), item.get("email", ""),
            item.get("socials", ""),
        )
        saved.append({"id": ident, "name": item["name"], "website": item.get("website", ""),
                      "source_url": item.get("source_url", "")})
    return {"found": len(results), "saved": len(saved), "skipped_duplicates": skipped, "companies": saved}


@mcp.tool()
def research_company_website(company_id: int) -> dict:
    """Read a saved company's public website, identify evidence-based website signals and save them."""
    company = _company(company_id)
    if not company.get("website"):
        raise ValueError("This company has no website saved yet.")
    profile = profile_website(company["website"])
    if profile.get("signals"):
        save_company_observations(company_id, profile["signals"])
    return {
        "company_id": company_id,
        "company_name": company["name"],
        "profile": profile,
        "note": "Website signals are heuristic observations, not proof of buying intent.",
    }


@mcp.tool()
def get_company_and_offer_profile() -> dict:
    """Read the business/product profile used to personalise outreach in this workspace."""
    return load_training()


@mcp.tool()
def list_prospects_contacts(limit: int = 100) -> list[dict]:
    """List saved prospect contacts and their current email status."""
    return list_contacts(max(1, min(int(limit), 500)))


@mcp.tool()
def list_outreach_campaigns() -> list[dict]:
    """List campaigns saved in the local Zero Hawk workspace."""
    return list_campaigns()


@mcp.tool()
def create_outreach_campaign(name: str, description: str = "") -> dict:
    """Create a campaign container. This does not start or send a campaign."""
    if not name.strip():
        raise ValueError("Campaign name is required.")
    campaign_id = add_campaign(name.strip(), description.strip())
    return {"id": campaign_id, "name": name.strip(), "status": "draft", "sending_started": False}


@mcp.tool()
def prepare_personalized_email_draft(
    company_id: int,
    contact_id: int,
    context: str = "",
    campaign_id: int | None = None,
) -> dict:
    """Write and save one personalised email draft for human review. Never approves or sends it."""
    company = _company(company_id)
    with connect() as conn:
        contact_row = conn.execute(
            "SELECT * FROM contacts WHERE id=? AND company_id=?",
            (contact_id, company_id),
        ).fetchone()
    if not contact_row:
        raise ValueError("Contact not found for this company.")
    contact = dict(contact_row)
    if not contact.get("email"):
        raise ValueError("Add a recipient email before preparing an email draft.")
    if is_suppressed(contact["email"]):
        raise ValueError("This recipient is on the suppression list and cannot be contacted.")
    if campaign_id is not None:
        with connect() as conn:
            exists = conn.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not exists:
            raise ValueError("Campaign not found.")
    training = load_training()
    prompt = f"""Prepare one concise, specific first-touch B2B email. Use only supported facts below.
If a detail is unknown, do not invent it. Do not claim a verified result, relationship or urgency.
Return exactly two sections: SUBJECT: on the first line, then BODY: and the email.
Business profile: {training}
Company: {company}
Contact: {contact}
Additional user context: {context}
"""
    result = ask_ai(
        prompt,
        system="You are Zero Hawk's careful outbound research and writing agent. Be accurate, relevant, respectful and concise. Never invent facts.",
    )
    subject, body = "", result.strip()
    lines = result.strip().splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).replace("BODY:", "", 1).strip()
    if not body:
        raise RuntimeError("The configured AI returned an empty draft.")
    draft_id = add_draft(body, company_id, contact_id, campaign_id, subject, "email")
    return {
        "draft_id": draft_id,
        "company": company["name"],
        "recipient": contact["email"],
        "subject": subject,
        "body": body,
        "status": "draft — awaiting your review",
        "sent": False,
        "approval_required": True,
    }


@mcp.tool()
def list_outreach_drafts(limit: int = 100) -> list[dict]:
    """List saved outreach drafts and their approval/sending statuses."""
    return list_drafts()[:max(1, min(int(limit), 500))]


@mcp.tool()
def read_recent_activity(limit: int = 50) -> list[dict]:
    """Read recent events recorded by Zero Hawk."""
    return list_activity(max(1, min(int(limit), 200)))


@mcp.tool()
def ask_configured_ai(prompt: str) -> str:
    """Ask the AI provider configured in Zero Hawk. This tool does not execute external actions."""
    return ask_ai(prompt)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
