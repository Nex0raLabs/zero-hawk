"""Real SMTP delivery and IMAP synchronization. Credentials are read only from environment variables."""
from __future__ import annotations
import email, imaplib, os, smtplib, ssl, uuid, datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from .db import connect, is_suppressed, log
from .verification import is_deliverable

def email_status():
    required=("OPENPROSPECT_SMTP_HOST","OPENPROSPECT_SMTP_USER","OPENPROSPECT_SMTP_PASSWORD","OPENPROSPECT_FROM_EMAIL")
    missing=[k for k in required if not os.getenv(k)]
    return {"configured":not missing,"missing":missing,"provider":"SMTP"}

def send_email(*,to:str,subject:str,body:str,unsubscribe_url:str,verification:dict,approved:bool=False):
    cfg=email_status()
    if not cfg["configured"]: raise RuntimeError("SMTP is not configured: "+", ".join(cfg["missing"]))
    if not approved: raise RuntimeError("Message must be explicitly approved before sending.")
    if not is_deliverable(verification) or verification.get("address","").lower()!=to.lower():
        raise RuntimeError("Recipient must have a current verified, non-catch-all email result.")
    if is_suppressed(to): raise RuntimeError("Recipient is on the suppression list.")
    daily_cap = max(1, min(int(os.getenv("OPENPROSPECT_DAILY_SEND_LIMIT", "25")), 100))
    with connect() as c:
        sent_today = c.execute("SELECT COUNT(*) FROM activity WHERE event=? AND date(created_at)=date(?)", ("email_sent", datetime.date.today().isoformat())).fetchone()[0]
    if sent_today >= daily_cap:
        raise RuntimeError("Daily sending limit reached (" + str(daily_cap) + ").")
    msg=EmailMessage(); msg["From"]=os.environ["OPENPROSPECT_FROM_EMAIL"]; msg["To"]=to
    msg["Subject"]=subject; msg["Date"]=formatdate(localtime=True); msg["Message-ID"]=make_msgid()
    msg["List-Unsubscribe"]=f"<{unsubscribe_url}>"; msg["List-Unsubscribe-Post"]="List-Unsubscribe=One-Click"
    msg.set_content(body.rstrip()+"\n\nTo stop receiving these messages, use the unsubscribe link: "+unsubscribe_url)
    host=os.environ["OPENPROSPECT_SMTP_HOST"]; port=int(os.getenv("OPENPROSPECT_SMTP_PORT","587"))
    with smtplib.SMTP(host,port,timeout=20) as server:
        server.ehlo(); server.starttls(context=ssl.create_default_context()); server.ehlo()
        server.login(os.environ["OPENPROSPECT_SMTP_USER"],os.environ["OPENPROSPECT_SMTP_PASSWORD"])
        server.send_message(msg)
    log("email_sent",f"{to} | {subject}")
    return {"sent":True,"message_id":msg["Message-ID"]}

def imap_status():
    keys=("OPENPROSPECT_IMAP_HOST","OPENPROSPECT_IMAP_USER","OPENPROSPECT_IMAP_PASSWORD")
    missing=[k for k in keys if not os.getenv(k)]
    return {"configured":not missing,"missing":missing}

def sync_imap(limit:int=50):
    from .conversations import ensure_schema
    ensure_schema()
    cfg=imap_status()
    if not cfg["configured"]: raise RuntimeError("IMAP is not configured: "+", ".join(cfg["missing"]))
    host=os.environ["OPENPROSPECT_IMAP_HOST"]; port=int(os.getenv("OPENPROSPECT_IMAP_PORT","993"))
    box=imaplib.IMAP4_SSL(host,port,ssl_context=ssl.create_default_context())
    added=0
    try:
        box.login(os.environ["OPENPROSPECT_IMAP_USER"],os.environ["OPENPROSPECT_IMAP_PASSWORD"])
        box.select(os.getenv("OPENPROSPECT_IMAP_FOLDER","INBOX"),readonly=True)
        typ,data=box.search(None,"UNSEEN")
        if typ!="OK": raise RuntimeError("IMAP search failed")
        for uid in data[0].split()[-max(1,min(limit,200)):]:
            typ,parts=box.fetch(uid,"(RFC822)")
            if typ!="OK": continue
            raw=next((p[1] for p in parts if isinstance(p,tuple)),None)
            if not raw: continue
            msg=email.message_from_bytes(raw)
            sender=email.utils.parseaddr(msg.get("From",""))[1].lower()
            subject=str(email.header.make_header(email.header.decode_header(msg.get("Subject",""))))
            mid=msg.get("Message-ID","").strip()
            text=""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type()=="text/plain" and not part.get_filename():
                        try:text+=part.get_content()
                        except Exception:pass
            elif msg.get_content_type()=="text/plain":
                try:text=msg.get_content()
                except Exception:pass
            from .conversations import add_message
            add_message("email", mid or str(uuid.uuid4()), sender, subject, text[:12000] or subject, "inbound")
            added+=1
            if any(term in (subject+" "+text).lower() for term in ("unsubscribe","stop emailing","remove me","opt out")):
                with connect() as c:c.execute("INSERT OR IGNORE INTO suppressions(value,reason) VALUES(?,?)",(sender,"Email opt-out detected in inbound reply"))
                log("email_optout_detected",sender)
        return {"synced":added}
    finally:
        try:box.logout()
        except Exception:pass
