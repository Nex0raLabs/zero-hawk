"""Evidence-based DNS and privacy readiness checks (not legal advice)."""
from __future__ import annotations
import socket
from urllib.parse import urlsplit
import dns.resolver

def dns_report(domain:str):
    domain=(domain or "").strip().lower().rstrip(".")
    if "://" in domain: domain=urlsplit(domain).hostname or ""
    if not domain or "/" in domain or "." not in domain: raise ValueError("Enter a valid domain name.")
    report={"domain":domain,"spf":{"status":"missing","records":[]},"dmarc":{"status":"missing","records":[]},"dkim":{"status":"not_tested","records":[]},"mx":{"status":"missing","records":[]},"notes":"DKIM selector is provider-specific; supply selectors in a future settings update. DNS presence does not prove alignment or deliverability."}
    def txt(name):
        try:return [b"".join(r.strings).decode("utf-8","replace") for r in dns.resolver.resolve(name,"TXT",lifetime=4)]
        except Exception:return []
    spf=[x for x in txt(domain) if x.lower().startswith("v=spf1")]
    dmarc=[x for x in txt("_dmarc."+domain) if x.lower().startswith("v=dmarc1")]
    report["spf"]={"status":"pass" if spf else "missing","records":spf}
    report["dmarc"]={"status":"pass" if dmarc else "missing","records":dmarc}
    try:
        mx=[str(x.exchange).rstrip(".") for x in dns.resolver.resolve(domain,"MX",lifetime=4)]
        report["mx"]={"status":"pass" if mx else "missing","records":mx}
    except Exception: pass
    report["dkim"]={"status":"not_tested","records":[]}
    return report

def privacy_checklist():
    return [
      {"item":"Document a lawful basis and purpose before collecting personal data","required":True},
      {"item":"Record the public source and collection date for each contact","required":True},
      {"item":"Provide clear sender identity and a working opt-out route","required":True},
      {"item":"Maintain and enforce a suppression list across all channels","required":True},
      {"item":"Set retention periods and securely delete data no longer needed","required":True},
      {"item":"Review cross-border processing, processor contracts and ODPC obligations","required":True},
      {"item":"Do not treat publicly visible contact details as automatic marketing consent","required":True},
    ]
