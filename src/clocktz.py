"""Heure affichée par le programme : heure de Windows (défaut) ou UTC, réglée par un clic sur l'horloge."""
import time

MODE = "local"          # "local", "both" (heure de Windows + UTC dans l'horloge) ou "utc"


def utc():
    return MODE == "utc"


def struct(t=None):
    return time.gmtime(t) if utc() else time.localtime(t)


def fmt(f="%H:%M", t=None, suffix=True):
    """Heure formatée dans le fuseau choisi ; « UTC » ajouté seulement en mode UTC."""
    return time.strftime(f, struct(t)) + (" UTC" if suffix and utc() else "")


def label(text):
    """« Heure » -> « Heure UTC » en mode UTC."""
    return text + (" UTC" if utc() else "")
