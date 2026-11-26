"""Phone normalisation to E.164, tuned for Kenya (+254) with a generic international fallback."""
from __future__ import annotations
import re

def normalize_phone(raw: str, default_country: str = "254") -> str:
    """Return an E.164 number like +254712345678, or '' if the input cannot be trusted."""
    if not raw:
        return ""
    s = re.split(r"(?:ext\.?|x|;|/|,)", str(raw).strip(), maxsplit=1, flags=re.I)[0]
    plus = s.strip().startswith("+")
    d = re.sub(r"\D", "", s)
    if not d:
        return ""
    if d.startswith("00"):
        d, plus = d[2:], True
    if plus:
        if d.startswith("254"):
            return "+" + d if len(d) == 12 else ""
        return "+" + d if 8 <= len(d) <= 15 else ""
    if default_country == "254":
        if d.startswith("254") and len(d) == 12:
            return "+" + d
        if d.startswith("0") and len(d) == 10:      # 0712 345 678, 020 xxx xxxx
            return "+254" + d[1:]
        if len(d) == 9 and d[0] in "71":             # 712345678 (mobile) 
            return "+254" + d
        return ""
    return "+" + d if 8 <= len(d) <= 15 else ""

def is_mobile_ke(e164: str) -> bool:
    """Kenyan mobile ranges start 7xx / 1xx after +254 (landlines such as Nairobi 20 do not)."""
    return bool(re.fullmatch(r"\+254[71]\d{8}", e164 or ""))

def whatsapp_eligible(e164: str) -> bool:
    return is_mobile_ke(e164) or bool(re.fullmatch(r"\+(?!254)\d{8,15}", e164 or ""))
