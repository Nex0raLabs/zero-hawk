"""Safe local Autopilot: periodic public-site profiling only; never sends messages."""
from __future__ import annotations
import json, threading, time
from datetime import datetime, timezone
from .db import list_companies, log, save_company_observations, db_path
from .profiling import profile_website

_lock = threading.Lock()
_stop = threading.Event()
_worker = None
_DEFAULTS = {"enabled": False, "interval_seconds": 900, "batch_size": 5,
             "last_started": None, "last_completed": None, "last_processed": 0, "last_errors": []}


def _settings_path():
    return db_path().with_name("autopilot.json")


def _read_settings():
    try:
        raw = json.loads(_settings_path().read_text("utf-8"))
        data = {**_DEFAULTS, **raw}
    except (OSError, ValueError, TypeError):
        data = dict(_DEFAULTS)
    data["interval_seconds"] = max(900, min(int(data.get("interval_seconds", 900)), 86400))
    data["batch_size"] = max(1, min(int(data.get("batch_size", 5)), 25))
    return data


def _write_settings(**updates):
    data = _read_settings(); data.update(updates)
    path = _settings_path(); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), "utf-8")
    temp.replace(path)
    return data


def run_once(limit=None, *, respect_stop=False):
    if not _lock.acquire(blocking=False):
        return {"busy": True, "processed": 0, "errors": []}
    processed = 0; errors = []
    settings = _read_settings()
    _write_settings(last_started=datetime.now(timezone.utc).isoformat())
    try:
        batch = settings["batch_size"] if limit is None else max(1, min(int(limit), 25))
        for company in list_companies(10000):
            if processed >= batch or (respect_stop and _stop.is_set()): break
            if not company.get("website"): continue
            try:
                result = profile_website(company["website"])
                if not result.get("error"):
                    save_company_observations(company["id"], result.get("signals", []))
                    log("autopilot_profiled", f"{company['name']}: score {result.get('score', 0)}")
                    processed += 1
            except Exception as exc:
                errors.append(f"{company['name']}: {exc}")
                log("autopilot_error", errors[-1])
            if not (respect_stop and _stop.is_set()): time.sleep(0.25)
        _write_settings(last_completed=datetime.now(timezone.utc).isoformat(),
                        last_processed=processed, last_errors=errors)
        return {"busy": False, "processed": processed, "errors": errors,
                "sending": "disabled; all outreach remains human-approved"}
    finally:
        _lock.release()


def start_loop(interval=None, batch_size=None):
    global _worker
    current = _read_settings()
    seconds = current["interval_seconds"] if interval is None else max(900, min(int(interval), 86400))
    batch = current["batch_size"] if batch_size is None else max(1, min(int(batch_size), 25))
    if _worker and _worker.is_alive():
        if not _stop.is_set():
            _write_settings(enabled=True, interval_seconds=seconds, batch_size=batch)
            return False
        # A paused cycle may still be finishing an in-flight HTTP request.
        _worker.join(timeout=5)
        if _worker.is_alive():
            raise RuntimeError("The previous Autopilot cycle is still finishing. Try again in a moment.")
    _write_settings(enabled=True, interval_seconds=seconds, batch_size=batch)
    _stop.clear()
    def work():
        while not _stop.is_set():
            try: run_once(respect_stop=True)
            except Exception as exc: log("autopilot_error", str(exc))
            _stop.wait(seconds)
    _worker = threading.Thread(target=work, name="zero-hawk-autopilot", daemon=True)
    _worker.start()
    log("autopilot_enabled", f"Safe profiling heartbeat enabled: {seconds}s")
    return True


def pause_loop():
    _stop.set()
    _write_settings(enabled=False)
    log("autopilot_disabled", "Autopilot paused by user")
    return True


def resume_saved_autopilot():
    """Resume only if the user previously left Autopilot enabled."""
    settings = _read_settings()
    if settings["enabled"]:
        return start_loop(settings["interval_seconds"], settings["batch_size"])
    return False


def loop_status():
    settings = _read_settings()
    running = bool(_worker and _worker.is_alive() and not _stop.is_set())
    return {**settings, "running": running,
            "enabled": bool(settings["enabled"] and running),
            "mode": "15-minute minimum heartbeat: public website profiling and signal capture only. It never automatically sends email or WhatsApp messages."}


def stop_worker_for_shutdown():
    """Stop this process's daemon worker without clearing the saved ON preference."""
    _stop.set()
