"""Copie JPG des images reçues dans un seul dossier (2.00, demande de VK3DNH).

Pour les « murs des dernières images reçues » des sites web (QSL.net demande des fichiers .jpg) :
chaque image reçue est copiée en JPEG, sous le même nom que l'original avec l'extension .jpg,
directement dans le dossier choisi (pas de sous-dossier par jour). L'enregistrement habituel ne
change pas ; ce dossier n'est jamais touché par le nettoyage des anciennes images.
"""
import os
import shutil

from PIL import Image

import imgfmt

QUALITY = 90


def is_jpeg(path):
    try:
        with open(path, "rb") as f:
            return f.read(3) == b"\xff\xd8\xff"
    except OSError:
        return False


def target(folder, path):
    """Nom de la copie : même nom que l'image reçue, extension .jpg, dans `folder`."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(folder, stem + ".jpg")


def make(folder, path, png=None, old=None):
    """Copie (ou convertit) l'image reçue `path` en JPEG dans `folder`. png : rendu PNG (SVG…), utilisé
    s'il existe. old : copie précédente de la même image (avant l'arrivée de l'indicatif), effacée.
    -> chemin de la copie."""
    os.makedirs(folder, exist_ok=True)
    dst = target(folder, path)
    tmp = dst + ".part"
    if is_jpeg(path):
        shutil.copyfile(path, tmp)                     # déjà en JPEG : copié tel quel, sans perte
    else:
        src = png if png and os.path.exists(png) else path
        im, _raw, _kind = imgfmt.load_source(src)      # AVIF, WebP, PNG, GIF (1re image), SVG…
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(tmp, "JPEG", quality=QUALITY, optimize=True)
    os.replace(tmp, dst)
    if old and os.path.abspath(old) != os.path.abspath(dst):
        try:
            os.remove(old)
        except OSError:
            pass
    return dst


def same_folder(a, b):
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except (TypeError, ValueError):
        return False
