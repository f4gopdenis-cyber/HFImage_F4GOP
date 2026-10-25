"""Traduction automatique des messages reçus dans la langue choisie dans le programme.

Le message part par radio tel qu'il a été écrit ; seule la station qui le reçoit le
traduit, pour l'afficher dans sa langue (l'original reste affiché en dessous).
La traduction passe par un service gratuit sur Internet (Google Traduction, puis
MyMemory en secours). Sans Internet, rien n'est traduit et le message s'affiche tel quel.
"""
import netssl
import json
import re
import threading
import urllib.parse
import urllib.request

TIMEOUT = 8
MAX_LEN = 1500
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HFImage"
_WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def worth(text):
    """Vaut-il la peine de traduire ? (au moins deux vrais mots : pas « 73 », ni un simple indicatif)"""
    return len(_WORD.findall(text or "")) >= 2


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with netssl.urlopen(req, TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _google(text, target):
    q = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text})
    data = _get("https://translate.googleapis.com/translate_a/single?" + q)
    out = "".join(seg[0] for seg in data[0] if seg and seg[0])
    src = data[2] if len(data) > 2 and isinstance(data[2], str) else ""
    return out, src


def _mymemory(text, target):
    q = urllib.parse.urlencode({"q": text, "langpair": "Autodetect|" + target})
    data = _get("https://api.mymemory.translated.net/get?" + q)
    out = (data.get("responseData") or {}).get("translatedText") or ""
    src = ""
    for m in data.get("matches") or []:
        src = (m.get("source") or "")[:2].lower()
        if src:
            break
    if "MYMEMORY WARNING" in out.upper() or "INVALID" in out.upper():
        return "", ""
    return out, src


def translate(text, target, services=None):
    """-> (texte traduit, langue d'origine) ou None (déjà dans la bonne langue, rien à traduire,
    ou service injoignable)."""
    text = (text or "").strip()
    if not text or not target or not worth(text):
        return None
    text = text[:MAX_LEN]
    for fn in services or (_google, _mymemory):
        try:
            out, src = fn(text, target)
        except Exception:
            continue
        out = (out or "").strip()
        if not out:
            continue
        src = (src or "").split("-")[0].lower()
        if src == target or out.casefold() == text.casefold():
            return None
        return out, src
    return None


def translate_async(text, target, done):
    """Traduit dans un fil à part ; done(résultat) est appelé depuis ce fil."""
    def run():
        try:
            res = translate(text, target)
        except Exception:
            res = None
        done(res)
    threading.Thread(target=run, daemon=True).start()

