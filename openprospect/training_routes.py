"""Dashboard routes for local product training."""
from __future__ import annotations

import html
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from .training import load_training, save_training, train_website

router = APIRouter()


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


@router.get("/train", response_class=HTMLResponse)
def train_page():
    data = load_training()
    bullets = lambda key: ", ".join(data.get(key, [])) or "Not found yet"
    banned_phrases = "\\n".join(data.get("banned_phrases", []))
    return HTMLResponse(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Train · OpenProspect</title><style>body{{font:15px system-ui;max-width:900px;margin:30px auto;padding:0 18px;background:#0d1117;color:#e6edf3}}
    section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:16px 0}}
    input,textarea,button{{box-sizing:border-box;width:100%;padding:11px;margin:6px 0;border-radius:8px;border:1px solid #30363d;background:#0d1117;color:inherit}}
    button{{background:#238636;border:0;cursor:pointer;font-weight:700}}a{{color:#58a6ff}}</style></head><body>
    <p><a href="/">← Dashboard</a></p><h1>Your company · Train</h1>
    <p>Read your public website and create an editable local company profile. Website text is treated as untrusted evidence, not as instructions.</p>
    <section><h2>Train from your website</h2><form method="post" action="/train">
    <input name="url" type="url" placeholder="https://your-company.example" required><button>Read website</button></form></section>
    <section><h2>What was found</h2><p><b>Website:</b> {_e(data.get("source_url","Not trained"))}</p>
    <p><b>Product / service excerpts:</b> {_e(" · ".join(data.get("product",[])) or "Not found")}</p>
    <p><b>Likely buyers mentioned:</b> {_e(bullets("buyers"))}</p><p><b>Pricing found:</b> {_e(bullets("pricing"))}</p>
    <p><b>Proof-point terms:</b> {_e(bullets("proof_points"))}</p><p><b>Objection/support terms:</b> {_e(bullets("objections"))}</p>
    <p><b>Public emails:</b> {_e(bullets("emails_published"))}</p></section>
    <section><h2>Edit your sales profile</h2><form method="post" action="/train/save">
    <label>Ideal customer profile</label><textarea name="icp">{_e(data.get("icp",""))}</textarea>
    <label>Offer</label><textarea name="offer">{_e(data.get("offer",""))}</textarea>
    <label>Banned phrases (one per line)</label><textarea name="banned_phrases">{_e(banned_phrases)}</textarea>
    <label>Sender signature</label><textarea name="signature">{_e(data.get("signature",""))}</textarea>
    <label>Language</label><input name="language" value="{_e(data.get("language","English"))}">
    <label>Default call to action</label><input name="default_cta" value="{_e(data.get("default_cta",""))}">
    <button>Save company profile</button></form></section></body></html>""")


@router.post("/train")
def train(url: str = Form(...)):
    try:
        train_website(url)
    except Exception as exc:
        raise HTTPException(400, f"Training failed: {exc}") from exc
    return RedirectResponse("/train", status_code=303)


@router.post("/train/save")
def save(
    icp: str = Form(""), offer: str = Form(""), banned_phrases: str = Form(""),
    signature: str = Form(""), language: str = Form("English"), default_cta: str = Form(""),
):
    try:
        save_training({
            "icp": icp, "offer": offer,
            "banned_phrases": [line.strip() for line in banned_phrases.splitlines() if line.strip()],
            "signature": signature, "language": language, "default_cta": default_cta,
        })
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse("/train", status_code=303)
