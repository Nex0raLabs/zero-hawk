"""Conservative autonomous pipeline runner. Sending remains approval-gated."""
from __future__ import annotations
import threading, time
from .db import list_companies, log
from .profiling import profile_website
from .db import save_company_observations
_lock=threading.Lock(); _stop=threading.Event(); _worker=None

def run_once(limit=5):
    if not _lock.acquire(blocking=False): return {"busy":True,"processed":0}
    processed=0; errors=[]
    try:
        for company in list_companies(max(1,min(int(limit),25))):
            if _stop.is_set(): break
            if not company.get("website"): continue
            try:
                result=profile_website(company["website"])
                if not result.get("error"):
                    save_company_observations(company["id"],result.get("signals",[]))
                    log("automation_profiled",f"{company['name']}: score {result.get('score',0)}")
                    processed+=1
            except Exception as exc:
                errors.append(f"{company['name']}: {exc}")
                log("automation_error",errors[-1])
            time.sleep(1)
        return {"busy":False,"processed":processed,"errors":errors,"sending":"disabled unless separately approved"}
    finally:_lock.release()

def start_loop(interval=3600):
    global _worker
    if _worker and _worker.is_alive(): return False
    _stop.clear()
    def work():
        while not _stop.is_set():
            run_once()
            _stop.wait(max(300,min(int(interval),86400)))
    _worker=threading.Thread(target=work,name="openprospect-autonomy",daemon=True);_worker.start()
    log("automation_started","Local profile-and-signal loop; no outbound messages")
    return True

def pause_loop():
    _stop.set();log("automation_paused","Autonomous loop paused");return True

def loop_status():return {"running":bool(_worker and _worker.is_alive() and not _stop.is_set()),"mode":"profile and signal only; outbound messages are never sent by the loop"}
