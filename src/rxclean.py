"""Nettoyage automatique des anciennes images reçues et envoyées.

Ne touche qu'aux sous-dossiers par jour (AAAA-MM-JJ) créés par HFImage depuis la
version 0.84, dans le dossier de réception, « envoyees » et « relecture ». Rien d'autre
n'est jamais effacé : ni les fichiers reçus (« fichiers »), ni les enregistrements, ni
les images rangées à plat par les versions précédentes, ni vos propres dossiers.
"""
import datetime
import os
import re
import shutil

DAY_DIR = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
SUBDIRS = ("", "envoyees", "relecture")
DEFAULT_DAYS = 30


def old_day_dirs(folder, days, today=None):
    """Sous-dossiers par jour plus anciens que « days » jours -> [chemin]."""
    today = today or datetime.date.today()
    limit = today - datetime.timedelta(days=max(1, int(days)))
    out = []
    for sub in SUBDIRS:
        top = os.path.join(folder, sub) if sub else folder
        try:
            names = os.listdir(top)
        except OSError:
            continue
        for n in names:
            m = DAY_DIR.match(n)
            p = os.path.join(top, n)
            if not m or not os.path.isdir(p) or os.path.islink(p):
                continue
            try:
                day = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            if day < limit:
                out.append(p)
    return sorted(out)


def _size(path):
    total = 0
    for d, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(d, f))
            except OSError:
                pass
    return total


def clean(folder, days, today=None):
    """Efface les sous-dossiers par jour trop anciens -> (dossiers effacés, octets libérés)."""
    n, freed = 0, 0
    for p in old_day_dirs(folder, days, today):
        size = _size(p)
        shutil.rmtree(p, ignore_errors=True)
        if not os.path.exists(p):
            n += 1
            freed += size
    return n, freed
