"""Sauvegarde / restauration d'HFImage dans un seul fichier .zip (1.93, idée de BH2RMX).

Parties (au choix) :
  « settings » : réglages (~/.hfimage*.json : programme, profils, préréglages de poste, site web),
                 sons (dossier wav : begin.wav, end.wav, textes waterfall), locators, stations ;
  « rx »       : images et fichiers reçus (dossier des images reçues, sauf « envoyees ») ;
  « tx »       : images envoyées (dossier « envoyees »).

À la restauration, les chemins enregistrés dans les réglages (dossier des images, galerie…) sont
adaptés au nouveau dossier personnel (autre nom d'utilisateur Windows). Les mots de passe FTP,
chiffrés pour le compte Windows d'origine, ne se relisent pas ailleurs : ils sont à retaper.
"""
import datetime
import glob
import json
import os
import zipfile

MANIFEST = "hfimage_sauvegarde.json"
PARTS = ("settings", "rx", "tx")
SETTINGS_TOP = ("locators.json", "stations.csv")
SKIP_RX = {"envoyees", "wav"}
SKIP_RX_FILES = {"journal.txt", "LICENCE.txt", "LICENSE_GPL-3.0.txt"}
STORED = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".jp2", ".zip", ".pdf", ".mp3", ".mp4")


def _walk(top, skip_dirs=(), skip_files=()):
    """Fichiers sous top -> [(chemin, chemin relatif avec /)]."""
    out = []
    if not os.path.isdir(top):
        return out
    for root, dirs, files in os.walk(top):
        rel_root = os.path.relpath(root, top)
        if rel_root == ".":
            dirs[:] = [d for d in dirs if d not in skip_dirs]
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for f in files:
            if rel_root == "." and f in skip_files:
                continue
            p = os.path.join(root, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            rel = f if rel_root == "." else os.path.join(rel_root, f)
            out.append((p, rel.replace(os.sep, "/")))
    return out


def collect(parts, home, out_dir, folder):
    """Fichiers de chaque partie -> [(chemin, nom dans le zip)]. home : dossier personnel ;
    out_dir : dossier HFImage des Documents ; folder : dossier des images reçues."""
    items = []
    folder = os.path.abspath(folder)
    if "settings" in parts:
        for p in sorted(glob.glob(os.path.join(home, ".hfimage*.json"))):
            items.append((p, "home/" + os.path.basename(p)))
        for name in SETTINGS_TOP:
            p = os.path.join(out_dir, name)
            if os.path.isfile(p):
                items.append((p, "out/" + name))
        for p, rel in _walk(os.path.join(out_dir, "wav")):
            items.append((p, "out/wav/" + rel))
    if "rx" in parts:
        skip_files = set(SKIP_RX_FILES)
        if os.path.abspath(out_dir) == folder:
            skip_files |= set(SETTINGS_TOP)          # déjà dans les réglages
        for p, rel in _walk(folder, SKIP_RX, skip_files):
            items.append((p, "rx/" + rel))
    if "tx" in parts:
        for p, rel in _walk(os.path.join(folder, "envoyees")):
            items.append((p, "tx/" + rel))
    return items


def size_of(items):
    total = 0
    for p, _ in items:
        try:
            total += os.path.getsize(p)
        except OSError:
            pass
    return total


def make(zip_path, parts, home, out_dir, folder, version="", progress=None):
    """Crée la sauvegarde. -> (nombre de fichiers, octets)."""
    items = collect(parts, home, out_dir, folder)
    total = max(1, size_of(items))
    done = 0
    man = {"app": "HFImage", "version": version, "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "parts": list(parts), "home": os.path.abspath(home), "out": os.path.abspath(out_dir),
           "folder": os.path.abspath(folder), "files": len(items)}
    tmp = zip_path + ".part"
    with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
        z.writestr(MANIFEST, json.dumps(man, indent=1, ensure_ascii=False))
        for p, arc in items:
            comp = zipfile.ZIP_STORED if p.lower().endswith(STORED) else zipfile.ZIP_DEFLATED
            try:
                z.write(p, arc, compress_type=comp)
            except OSError:
                continue                              # fichier disparu ou verrouillé : on continue
            try:
                done += os.path.getsize(p)
            except OSError:
                pass
            if progress:
                progress(done / total)
    os.replace(tmp, zip_path)
    return len(items), done


def read_manifest(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        try:
            man = json.loads(z.read(MANIFEST).decode("utf-8"))
        except KeyError:
            raise ValueError("ce fichier n'est pas une sauvegarde d'HFImage")
    if man.get("app") != "HFImage":
        raise ValueError("ce fichier n'est pas une sauvegarde d'HFImage")
    return man


def _safe_rel(rel):
    """Nom dans le zip -> chemin relatif sûr (jamais en dehors du dossier visé), ou None."""
    rel = rel.replace("\\", "/")
    if rel.startswith("/") or ":" in rel.split("/")[0]:
        return None
    parts = [x for x in rel.split("/") if x not in ("", ".")]
    if not parts or any(x == ".." for x in parts):
        return None
    return os.path.join(*parts)


def _remap_text(text, pairs):
    """Remplace les anciens chemins par les nouveaux, dans le texte d'un fichier JSON (chemins
    écrits tels quels ou avec les barres obliques inverses doublées)."""
    for old, new in pairs:
        if not old or old == new:
            continue
        for o, n in ((old, new), (json.dumps(old)[1:-1], json.dumps(new)[1:-1])):
            text = text.replace(o, n)
    return text


def restore(zip_path, home, out_dir, folder, parts=None, progress=None):
    """Remet en place. folder : dossier des images reçues sur CE PC (si l'ancien n'existe pas).
    -> dict(files, parts, folder) ; folder = dossier où les images ont été remises."""
    man = read_manifest(zip_path)
    parts = [p for p in (parts or man.get("parts") or PARTS) if p in PARTS]
    old_home, old_out, old_folder = man.get("home", ""), man.get("out", ""), man.get("folder", "")
    pairs = [(old_home, os.path.abspath(home))]
    # dossier des images : l'ancien chemin (adapté au nouveau dossier personnel) s'il est utilisable
    new_folder = _remap_text(old_folder, pairs) if old_folder else folder
    drive = os.path.splitdrive(new_folder)[0]
    if not new_folder or (drive and not os.path.exists(drive + os.sep)):
        new_folder = folder
        pairs.insert(0, (old_folder, os.path.abspath(folder)))
    roots = {"home": home, "out": out_dir, "rx": new_folder, "tx": os.path.join(new_folder, "envoyees")}
    want = {"home": "settings", "out": "settings", "rx": "rx", "tx": "tx"}
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        infos = [i for i in z.infolist() if not i.is_dir() and i.filename != MANIFEST]
        total = max(1, sum(i.file_size for i in infos))
        done = 0
        for info in infos:
            top, _, rest = info.filename.partition("/")
            if top not in roots or want[top] not in parts:
                continue
            rel = _safe_rel(rest)
            if rel is None:
                continue
            if top == "home" and not (rel.startswith(".hfimage") and rel.endswith(".json") and os.sep not in rel):
                continue                               # dans le dossier personnel : nos réglages seulement
            dst = os.path.join(roots[top], rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            data = z.read(info)
            if dst.lower().endswith(".json"):
                try:
                    data = _remap_text(data.decode("utf-8"), pairs).encode("utf-8")
                except UnicodeDecodeError:
                    pass
            with open(dst, "wb") as f:
                f.write(data)
            n += 1
            done += info.file_size
            if progress:
                progress(done / total)
    return {"files": n, "parts": parts, "folder": new_folder, "date": man.get("date", ""),
            "version": man.get("version", "")}
