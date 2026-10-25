"""Connexions HTTPS : certificats de Windows + liste « certifi » (celle de Firefox).

Python vérifie les sites avec les certificats racine de Windows. Sur certains PC, il manque
celui dont GitHub a besoin (Windows ne le télécharge qu'à la première visite du site dans un
navigateur) : « CERTIFICATE_VERIFY_FAILED ». On ajoute donc la liste de certificats fournie
avec le programme ; la vérification reste complète (rien n'est désactivé).
"""
import ssl
import urllib.request

_CTX = None


def context():
    global _CTX
    if _CTX is None:
        ctx = ssl.create_default_context()           # certificats du système (Windows, Linux)
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        _CTX = ctx
    return _CTX


def urlopen(req, timeout):
    return urllib.request.urlopen(req, timeout=timeout, context=context())


def explain(e):
    """Erreur de certificat -> explication claire (sinon le texte de l'erreur)."""
    t = str(e)
    if "CERTIFICATE_VERIFY_FAILED" in t:
        return ("certificat de sécurité du site refusé : vérifiez la date et l'heure du PC ; un antivirus "
                "qui analyse les connexions HTTPS peut aussi en être la cause (autorisez HFImage)")
    return t
