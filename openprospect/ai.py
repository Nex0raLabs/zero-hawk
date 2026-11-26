from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


def _local_settings() -> dict[str, Any]:
    from .db import db_path
    path = db_path().parent / "ai-settings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_provider_settings(provider: str, model: str = "", base_url: str = "") -> dict[str, Any]:
    provider = provider.strip().lower()
    allowed = {"ollama", "claude-code", "codex", "openai-compatible", "anthropic"}
    if provider not in allowed:
        raise ValueError("Choose a supported AI provider.")
    from .db import db_path
    path = db_path().parent / "ai-settings.json"
    settings = {"provider": provider, "model": model.strip(), "base_url": base_url.strip()}
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings


def _setting(name: str, env_name: str, default: str = "") -> str:
    return str(_local_settings().get(name) or os.getenv(env_name, default))


def provider_name() -> str:
    return _setting("provider", "OPENPROSPECT_AI_PROVIDER", "ollama").strip().lower()


def provider_status() -> dict[str, Any]:
    provider = provider_name()
    if provider in {"claude-code", "claude"}:
        command = shutil.which("claude")
        return {"provider": "claude-code", "connected": False, "status": "Installed; not yet tested" if command else "Not connected", "fix": "Install Claude Code CLI and sign in with your existing subscription."}
    if provider in {"codex", "codex-cli"}:
        command = shutil.which("codex")
        return {"provider": "codex", "connected": False, "status": "Installed; not yet tested" if command else "Not connected", "fix": "Install Codex CLI and sign in with your existing ChatGPT account."}
    if provider == "ollama":
        base = os.getenv("OPENPROSPECT_AI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        model = os.getenv("OPENPROSPECT_AI_MODEL", "llama3.2")
        return {"provider": provider, "connected": False, "status": "Not connected", "fix": f"Start Ollama, pull {model}, then test the connection at {base}."}
    if provider in {"anthropic", "openai-compatible"}:
        key = os.getenv("OPENPROSPECT_AI_API_KEY", "")
        env_base = "ANTHROPIC_BASE_URL" if provider == "anthropic" else "OPENPROSPECT_AI_BASE_URL"
        default_base = "https://api.anthropic.com" if provider == "anthropic" else "https://api.openai.com/v1"
        base = _setting("base_url", env_base, default_base)
        return {"provider": provider, "connected": False, "status": "Configured; not yet tested" if key and base else "Not connected", "fix": "Set the provider URL, model and API key in your private .env file. Provider usage may cost money."}
    return {"provider": provider, "connected": False, "status": "Not connected", "fix": "Choose ollama, claude-code, codex, anthropic or openai-compatible."}


def _ask_cli(provider: str, prompt: str, system: str) -> str:
    if provider in {"claude-code", "claude"}:
        command = shutil.which("claude")
        if not command:
            raise RuntimeError("Claude Code CLI is not installed or not on PATH.")
        args = [command, "-p", "--output-format", "text", "--append-system-prompt", system, prompt]
    else:
        command = shutil.which("codex")
        if not command:
            raise RuntimeError("Codex CLI is not installed or not on PATH.")
        combined = f"{system}\n\n{prompt}"
        args = [command, "exec", "--skip-git-repo-check", combined]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=180, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{provider} CLI timed out after 180 seconds.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-1200:]
        raise RuntimeError(f"{provider} CLI failed: {detail or 'no diagnostic output'}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"{provider} CLI returned an empty response.")
    return output


def ask_ai(prompt: str, system: str = "You are a helpful business research and outreach assistant.") -> str:
    provider = provider_name()
    model = os.getenv("OPENPROSPECT_AI_MODEL", "")
    key = os.getenv("OPENPROSPECT_AI_API_KEY", "")
    base = os.getenv("OPENPROSPECT_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    if provider in {"claude-code", "claude", "codex", "codex-cli"}:
        return _ask_cli(provider, prompt, system)

    if provider == "ollama":
        base = os.getenv("OPENPROSPECT_AI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        model = model or "llama3.2"

    if provider == "anthropic":
        base = _setting("base_url", "ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        model = model or "claude-3-5-haiku-latest"
        if not key:
            raise RuntimeError("Set OPENPROSPECT_AI_API_KEY for the Anthropic provider.")
        payload = {"model": model, "max_tokens": 1200, "system": system, "messages": [{"role": "user", "content": prompt}]}
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        req = urllib.request.Request(base + "/v1/messages", data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=90) as res:
            data = json.loads(res.read())
        return "".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")

    if not model:
        raise RuntimeError("Set OPENPROSPECT_AI_MODEL in .env before using AI.")
    if provider not in {"ollama", "openai-compatible"}:
        raise RuntimeError(f"Unsupported AI provider: {provider}")
    payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    headers = {"content-type": "application/json"}
    if key:
        headers["authorization"] = "Bearer " + key
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as res:
        data = json.loads(res.read())
    return data["choices"][0]["message"]["content"]


def test_ai_connection() -> dict[str, Any]:
    provider = provider_name()
    answer = ask_ai("Reply with exactly: OPENPROSPECT CONNECTION OK", system="You are testing an AI provider connection. Follow the user instruction exactly.")
    return {"provider": provider, "connected": bool(answer.strip()), "response": answer.strip()[:300]}
