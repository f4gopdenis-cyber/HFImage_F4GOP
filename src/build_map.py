"""Fabrique carte.bin (fond de la carte des stations) à partir de Natural Earth (domaine public).

Fichiers GeoJSON nécessaires (https://github.com/nvkelso/natural-earth-vector, dossier geojson) :
  ne_50m_admin_0_countries.geojson, ne_50m_lakes.geojson, ne_10m_populated_places.geojson
(2.30, d'après BH2RMX : noms des pays et des villes dans chaque langue du programme)

Utilisation :  python build_map.py [dossier_des_geojson] [tolérance_en_degrés]   (défaut : . et 0.02)
"""
import json, os, zlib, sys
import numpy as np
NE = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/\\") + os.sep
TOL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02

def dp(pts, tol):
    """Douglas-Peucker itératif."""
    pts = np.asarray(pts, float)
    if len(pts) < 5:
        return pts
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2: continue
        p, q = pts[a], pts[b]
        seg = pts[a + 1:b]
        d = q - p
        n = np.hypot(*d)
        if n == 0:
            dist = np.hypot(*(seg - p).T)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / n
        i = int(np.argmax(dist))
        if dist[i] > tol:
            k = a + 1 + i; keep[k] = True
            stack += [(a, k), (k, b)]
    return pts[keep]

def enc(ring):
    r = dp(ring, TOL)
    if len(r) < 4: return None
    q = np.round(r * 100).astype(int)
    out = [int(q[0, 0]), int(q[0, 1])]
    for i in range(1, len(q)):
        out += [int(q[i, 0] - q[i - 1, 0]), int(q[i, 1] - q[i - 1, 1])]
    return out

def polys(g):
    return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]

LANGS = ("de", "es", "it", "ru", "zh")
# noms courts et neutres (le nom officiel complet prendrait trop de place sur la carte)
SHORT = {"China": {"fr": "Chine", "de": "China", "es": "China", "it": "Cina", "ru": "Китай", "zh": "中国"},
         "Taiwan": {"fr": "Taïwan", "de": "Taiwan", "es": "Taiwán", "it": "Taiwan", "ru": "Тайвань", "zh": "台湾"}}
# villes : noms actuels (BH2RMX) et ville natale de BH2RMX visible
CITY_FIX = {"Jinxi": {"zh": "葫芦岛"}, "Hailar": {"zh": "呼伦贝尔"}}
CITY_RANK = {"Jinzhou": 3}

def names(p, keys, base, fix=None):
    """{langue: nom} pour les langues où le nom diffère du nom de base."""
    out = {}
    for lg in LANGS:
        v = (fix or {}).get(lg) or p.get(keys + lg.upper()) or ""
        if v and v != base:
            out[lg] = v
    return out

data = {"countries": [], "lakes": [], "cities": []}
npts = 0
for f in json.load(open(NE + "ne_50m_admin_0_countries.geojson"))["features"]:
    p = f["properties"]
    rings = []
    for poly in polys(f["geometry"]):
        for ring in poly[:1]:                  # contour extérieur (les trous sont rares à cette échelle)
            e = enc(ring)
            if e: rings.append(e); npts += len(e) // 2
    fix = SHORT.get(p["NAME"], {})
    data["countries"].append({"c": p["MAPCOLOR7"], "n": p["NAME"], "nf": fix.get("fr") or p.get("NAME_FR") or p["NAME"],
                              "t": names(p, "NAME_", p["NAME"], fix),
                              "l": [round(p["LABEL_X"] * 100), round(p["LABEL_Y"] * 100), p["LABELRANK"]],
                              "r": rings})
for f in json.load(open(NE + "ne_50m_lakes.geojson"))["features"]:
    if f["properties"].get("scalerank", 9) > 2: continue
    for poly in polys(f["geometry"]):
        e = enc(poly[0])
        if e: data["lakes"].append(e); npts += len(e) // 2
for f in json.load(open(NE + "ne_10m_populated_places.geojson"))["features"]:
    p = f["properties"]
    rank = CITY_RANK.get(p["NAME"], p["SCALERANK"])
    if rank > 4 and not p["ADM0CAP"]: continue
    t = names(p, "NAME_", p["NAME"], CITY_FIX.get(p["NAME"]))
    if p.get("NAME_FR") and p["NAME_FR"] != p["NAME"]:
        t["fr"] = p["NAME_FR"]
    data["cities"].append([p["NAME"], round(p["LONGITUDE"] * 100), round(p["LATITUDE"] * 100),
                           rank, 1 if p["ADM0CAP"] else 0] + ([t] if t else []))
raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
z = zlib.compress(raw, 9)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "carte.bin"), "wb").write(z)
print(f"tol {TOL}: {npts} points, {len(data['cities'])} villes, json {len(raw)//1024} Ko -> zlib {len(z)//1024} Ko")
