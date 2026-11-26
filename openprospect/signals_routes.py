"""Dashboard screen for explainable, editable buying signals."""
from __future__ import annotations

import html
import json

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import list_observations
from .profiling import load_signal_rules, save_signal_rules

router = APIRouter()


@router.get("/signals", response_class=HTMLResponse)
def signals_page():
    rules = load_signal_rules()
    observations = list_observations(200)
    rows = "".join(
        f"<tr><td>{html.escape(row['company_name'])}</td><td>{html.escape(row['code'])}</td>"
        f"<td>{html.escape(row['label'])}</td><td>{row['weight']}</td>"
        f"<td>{row['confidence']:.0%}</td><td><a href='{html.escape(row['evidence_url'], quote=True)}'>Evidence</a></td></tr>"
        for row in observations
    )
    raw = html.escape(json.dumps(rules, indent=2, ensure_ascii=False))
    return HTMLResponse(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Signals · OpenProspect</title><style>body{{font:15px system-ui;max-width:1100px;margin:30px auto;padding:0 18px;background:#0d1117;color:#e6edf3}}
    section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:16px 0}}
    textarea,button{{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #30363d;background:#0d1117;color:inherit}}
    textarea{{min-height:360px;font:13px ui-monospace,monospace}}button{{background:#238636;border:0;cursor:pointer;font-weight:700}}
    table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;border-bottom:1px solid #30363d;text-align:left}}a{{color:#58a6ff}}</style></head><body>
    <p><a href="/">← Dashboard</a></p><h1>Buying signals</h1>
    <p>Signals are deterministic website observations with evidence links and confidence. They are clues for human review, not verified claims about a business.</p>
    <section><h2>Configure signal rules</h2><p>Edit built-in weights and add custom keyword rules. Custom rules require a unique uppercase code, label, keywords, weight (0–30) and enabled flag.</p>
    <form method="post" action="/signals"><textarea name="rules_json" spellcheck="false">{raw}</textarea><button>Save signal rules</button></form></section>
    <section><h2>Recent observations</h2><table><tr><th>Company</th><th>Code</th><th>Signal</th><th>Weight</th><th>Confidence</th><th>Evidence</th></tr>{rows or "<tr><td colspan='6'>No signals collected yet. Profile a company website first.</td></tr>"}</table></section>
    </body></html>""")


@router.post("/signals")
def save_signals(rules_json: str = Form(...)):
    try:
        payload = json.loads(rules_json)
        if not isinstance(payload, dict):
            raise ValueError("Signal rules must be a JSON object.")
        save_signal_rules(payload)
    except Exception as exc:
        raise HTTPException(400, f"Could not save signal rules: {exc}") from exc
    return RedirectResponse("/signals", status_code=303)
