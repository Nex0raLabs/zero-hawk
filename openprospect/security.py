"""Private local dashboard sign-in and request boundary."""
from __future__ import annotations

import hmac
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .db import db_path


def token_path() -> Path:
    return db_path().parent / "dashboard-token"


def get_dashboard_token() -> str:
    path = token_path()
    if not path.exists():
        token = secrets.token_urlsafe(32)
        path.write_text(token, encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return path.read_text(encoding="utf-8").strip()


def login_page() -> str:
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Zero Hawk · Sign in</title><style>
    body{font:15px system-ui;background:#0d1117;color:#e6edf3;display:grid;place-items:center;min-height:90vh;margin:0}
    main{width:min(420px,calc(100% - 40px));background:#161b22;border:1px solid #30363d;border-radius:16px;padding:24px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #30363d;background:#0d1117;color:inherit}
    button{background:#238636;border:0;font-weight:700;cursor:pointer}small{color:#8b949e}</style></head><body>
    <main><h1>◈ Zero Hawk</h1><p>Private local dashboard. Paste your dashboard token or open the private link printed by the command.</p>
    <form id="login"><input id="token" type="password" autocomplete="current-password" placeholder="Dashboard token" required>
    <button>Sign in</button></form><p id="status"><small>Your token stays in this browser session and is exchanged for a local-only session cookie.</small></p></main>
    <script>
    const status=document.getElementById('status'),field=document.getElementById('token');
    async function signIn(token){status.textContent='Checking token…';
      const response=await fetch('/auth/exchange',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
      if(response.ok){history.replaceState(null,'',location.pathname);location.replace('/');}
      else status.textContent='Token not accepted. Run zero-hawk dashboard to print a fresh private link.';
    }
    document.getElementById('login').addEventListener('submit',e=>{e.preventDefault();signIn(field.value);});
    const params=new URLSearchParams(location.hash.slice(1));const linkToken=params.get('token');
    if(linkToken)signIn(linkToken);
    </script></body></html>"""


def install_security(app: FastAPI) -> None:
    """Require a private token cookie and accept only loopback Host headers."""
    @app.middleware("http")
    async def local_dashboard_guard(request: Request, call_next):
        host = request.url.hostname or ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            return JSONResponse({"detail": "Zero Hawk only accepts local connections."}, status_code=403)

        if request.url.path == "/auth/exchange" and request.method == "POST":
            try:
                payload = await request.json()
                supplied = str(payload.get("token", ""))
            except Exception:
                supplied = ""
            if not hmac.compare_digest(supplied, get_dashboard_token()):
                return JSONResponse({"detail": "Invalid dashboard token."}, status_code=401)
            response = JSONResponse({"ok": True})
            response.set_cookie(
                "zero_hawk_session", get_dashboard_token(),
                httponly=True, secure=False, samesite="strict", path="/",
                max_age=60 * 60 * 24 * 30,
            )
            return response

        if request.url.path == "/auth/logout" and request.method == "POST":
            response = RedirectResponse("/", status_code=303)
            response.delete_cookie("zero_hawk_session", path="/", samesite="strict")
            return response

        if request.url.path == "/unsubscribe" and request.method in {"GET", "POST"}:
            return await call_next(request)

        if request.url.path == "/api/whatsapp/inbound" and request.method == "POST":
            import os
            expected = os.getenv("WA_SIDECAR_TOKEN", "")
            supplied = request.headers.get("authorization", "")
            if expected and hmac.compare_digest(supplied, "Bearer " + expected):
                return await call_next(request)
            return JSONResponse({"detail": "Invalid sidecar authentication."}, status_code=401)

        session = request.cookies.get("zero_hawk_session", "")
        if not hmac.compare_digest(session, get_dashboard_token()):
            if request.method in {"GET", "HEAD"}:
                return HTMLResponse(login_page(), status_code=200)
            return JSONResponse({"detail": "Sign in to the local dashboard first."}, status_code=401)

        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                from urllib.parse import urlsplit
                origin_host = urlsplit(origin).netloc.lower()
                if origin_host != request.headers.get("host", "").lower():
                    return JSONResponse({"detail": "Cross-origin request blocked."}, status_code=403)
            if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
                return JSONResponse({"detail": "Cross-origin request blocked."}, status_code=403)

        return await call_next(request)
