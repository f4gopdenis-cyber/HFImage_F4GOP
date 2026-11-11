"""2.31 (M7WUV) : carte QSL à la taille de son fond, et modèles de carte enregistrés."""
import gc
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402
import qsl  # noqa: E402


class Taille(unittest.TestCase):
    def test_taille_du_fond(self):
        for src, want in (((1920, 1080), (1920, 1080)), ((800, 1200), (800, 1200)),
                          ((3000, 2000), (2000, 1333)), ((400, 300), (960, 720))):
            c = qsl.make_card(Image.new("RGB", src, "#456"), "M7WUV", "JO01BM", "PD0CIF", "7.058 MHz",
                              "SNR +9 dB", "TNX QSO, 73 !")
            self.assertEqual(c.size, want)
        self.assertEqual(qsl.make_card(None, "M7WUV").size, (qsl.W, qsl.H))

    def test_textes_dans_la_carte(self):
        for src in ((1920, 1080), (800, 1200), (2000, 600)):
            b = {}
            c = qsl.make_card(Image.new("RGB", src), "M7WUV", "JO01BM", "PD0CIF", "7.058 MHz", "SNR +9 dB",
                              "TNX QSO, 73 !", boxes=b)
            for k, (x0, y0, x1, y1) in b.items():
                self.assertTrue(0 <= x0 < x1 <= c.width and 0 <= y0 < y1 <= c.height, (src, k))

    def test_meme_place_en_grand(self):
        st = {"pos": {"call": [0.1, 0.3]}}
        bg = Image.new("RGB", (1920, 1200))
        small, big = {}, {}
        qsl.make_card(bg, "M7WUV", style=st, boxes=small, size=(480, 300))
        qsl.make_card(bg, "M7WUV", style=st, boxes=big)
        self.assertAlmostEqual(big["call"][0] / 1920, small["call"][0] / 480, delta=0.01)
        self.assertAlmostEqual(big["call"][1] / 1200, small["call"][1] / 300, delta=0.01)


class Modeles(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        d = tempfile.mkdtemp()
        self.conf = os.path.join(d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "M7WUV", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a._closing = True
        self.a.destroy()
        gc.collect()
        self.p.stop()

    def _walk(self, w):
        yield w
        for c in w.winfo_children():
            yield from self._walk(c)

    def test_enregistrer_et_choisir(self):
        a = self.a
        a.src_img = Image.new("RGB", (1600, 900), (10, 80, 160))
        a.qsl_dialog()
        a.update()
        win = [w for w in a.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "Carte QSL"][-1]
        ws = list(self._walk(win))
        btn = lambda t: next(w for w in ws if isinstance(w, tk.ttk.Button) and w.cget("text") == t)
        cbm = next(w for w in ws if isinstance(w, tk.ttk.Combobox) and w.cget("width") == 18
                   and "Arial" not in w.cget("values"))
        with mock.patch("tkinter.simpledialog.askstring", return_value="Londres"):
            btn("Enregistrer le modèle…").invoke()
        m = a.conf["qsl_models"]["Londres"]
        self.assertTrue(os.path.exists(m["bg"]))
        with Image.open(m["bg"]) as im:
            self.assertEqual(im.size, (1600, 900))
        # on change le style, puis on reprend le modèle
        btn("Style d'origine").invoke()
        a.conf["qsl_models"]["Londres"]["style"]["call"] = "#ff0000"
        cbm.set("Londres")
        cbm.event_generate("<<ComboboxSelected>>")
        a.update()
        sw = [w for w in ws if isinstance(w, tk.Button) and w.cget("bg") == "#ff0000"]
        self.assertTrue(sw)
        with mock.patch("tkinter.messagebox.askyesno", return_value=True):
            btn("Supprimer").invoke()
        self.assertNotIn("Londres", a.conf["qsl_models"])
        self.assertFalse(os.path.exists(m["bg"]))
        win.destroy()
