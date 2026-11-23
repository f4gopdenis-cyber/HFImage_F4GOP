"""2.50 (signalé par Keith Woodley) : chaque message du journal a sa traduction (rien ne reste en
français quand le programme est en anglais)."""
import ast
import glob
import os
import re
import sys
import unittest

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)
import i18n  # noqa: E402

PAREIL = {"Format {0} ({1}).", "HamDRM (EasyPal): {0}, {1} s -> {2}"}     # identiques en anglais
FRANCAIS = re.compile(r"[éèàçêù]| de | des | le | la | pour | sur |Annonce|Hybride|Serveur|Présence")


def messages():
    """Messages du journal écrits dans le code : self.log(…), log(…), self.ui(self.log, …)."""
    out = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.py"))):
        if "i18n" in os.path.basename(f):
            continue
        with open(f, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
            a, target = node.args, None
            if name == "log" and a:
                target = a[0]
            elif name == "ui" and len(a) >= 2 and isinstance(a[0], ast.Attribute) and a[0].attr == "log":
                target = a[1]
            if isinstance(target, ast.JoinedStr):
                parts, k = [], 0
                for v in target.values:
                    if isinstance(v, ast.Constant):
                        parts.append(v.value)
                    else:
                        parts.append("{%d}" % k)
                        k += 1
                s = "".join(parts)
            elif isinstance(target, ast.Constant) and isinstance(target.value, str):
                s = target.value
            else:
                continue
            if re.search(r"[a-zéèàç]{3}", s):
                out.append((os.path.basename(f), node.lineno, s))
    return out


class JournalTraduit(unittest.TestCase):
    def test_anglais(self):
        old = i18n.get_lang()
        try:
            i18n.set_lang("en")
            manque = []
            for f, line, s in messages():
                if s in PAREIL:
                    continue
                sample = re.sub(r"\{(\d)\}", lambda m: "ZZ%sZZ" % m.group(1), s)
                t = i18n.tr(sample)
                if t == sample or FRANCAIS.search(t):
                    manque.append(f"{f}:{line} {s}")
            self.assertEqual(manque, [], "messages du journal sans traduction")
        finally:
            i18n.set_lang(old)

    def test_ligne_de_keith(self):
        old = i18n.get_lang()
        try:
            i18n.set_lang("en")
            self.assertEqual(i18n.tr("Annonce hybride éclair (DATAC13) : empreinte b39a972e8339, 287729 octets"),
                             "Flash hybrid announcement (DATAC13): fingerprint b39a972e8339, 287729 bytes")
            self.assertEqual(i18n.tr("Serveur : 1 ancienne(s) image(s) effacée(s) (gardées : 3)."),
                             "Server: 1 old picture(s) deleted (kept: 3).")
        finally:
            i18n.set_lang(old)


if __name__ == "__main__":
    unittest.main()
