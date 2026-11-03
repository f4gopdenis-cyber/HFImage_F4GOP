"""2.01 (demande de F1ABL) : jusqu'à 8 images reçues incrustées dans l'image TX ; les 4 premières dans
les coins, les 4 suivantes au milieu des bords (en haut, en bas, à gauche, à droite)."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Huit(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.A = app.App

    def stub(self):
        A = self.A
        s = types.SimpleNamespace(conf={}, pips=[], PIP_MAX_N=A.PIP_MAX_N, PIP_CORNERS=A.PIP_CORNERS,
                                  PIP_EDGES=A.PIP_EDGES)
        for n in ("_pip_slot_layout", "_pip_new", "_pip_make_room"):
            setattr(s, n, getattr(A, n).__get__(s))
        return s

    def test_huit_emplacements_distincts(self):
        self.assertEqual(self.A.PIP_MAX_N, 8)
        s = self.stub()
        for i in range(8):
            s.pips.append(s._pip_new({"path": f"img{i}.jpg", "call": f"F{i}AA"}))
        places = [(p["corner"], None) if not p.get("pos") else (None, tuple(p["pos"])) for p in s.pips]
        self.assertEqual(len(set(places)), 8)                       # aucune ne se superpose
        self.assertEqual([p["corner"] for p in s.pips[:4]], list(self.A.PIP_CORNERS))
        self.assertEqual([tuple(p["pos"]) for p in s.pips[4:]], list(self.A.PIP_EDGES))

    def test_place_sur_l_image(self):
        import trafic
        s = self.stub()
        s.conf["pip_size"] = "moyenne"                              # 1re image en taille moyenne (défaut)
        for i in range(8):
            s.pips.append(s._pip_new({"path": f"img{i}.jpg", "call": f"F{i}AA"}))
        rects = []
        for p in s.pips:
            r = trafic.pip_layout((1024, 768), (300, 200), "de F4AA — +5 dB", p["corner"], p["size"], p["pos"],
                                  p["scale"])
            rects.append(r)
        boxes = [(x, y, x + W, y + H) for x, y, W, H, *_ in rects]
        for k, a in enumerate(boxes):
            self.assertTrue(0 <= a[0] and 0 <= a[1] and a[2] <= 1024 and a[3] <= 768, a)   # dans l'image
            for b in boxes[k + 1:]:
                overlap = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
                self.assertFalse(overlap, (a, b))                  # taille « petite » : pas de chevauchement


if __name__ == "__main__":
    unittest.main()


class TailleChoisieGardee(Huit):
    def test_taille_libre_non_touchee(self):
        s = self.stub()
        for i in range(4):
            s.pips.append(s._pip_new({"path": f"img{i}.jpg", "call": f"F{i}AA"}))
        s.pips[1]["scale"] = 0.5                                   # réglée à la souris : gardée
        s.pips[2]["size"] = "grande"
        s.pips.append(s._pip_new({"path": "img4.jpg", "call": "F4AA"}))
        self.assertEqual(s.pips[1]["scale"], 0.5)
        self.assertEqual(s.pips[2]["size"], "petite")
