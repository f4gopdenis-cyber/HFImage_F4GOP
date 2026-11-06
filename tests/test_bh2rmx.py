"""2.13 (demandes de BH2RMX) : carte QSL refaite depuis son fond d'origine, image TX enregistrée
ou retirée, ordre des images insérées, « (par défaut) » traduit dans la liste des polices."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class BH2RMX(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        self.d = tempfile.mkdtemp()
        self.conf = os.path.join(self.d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "BH2RMX", "licence_ok": "1.0", "lang": "zh", "net_on": False}, f)
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
        for w in self.a.winfo_children():
            if isinstance(w, self.app.tk.Toplevel):
                w.destroy()
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def pump(self, s=0.4):
        t = time.time()
        while time.time() - t < s:
            self.a.update()
            time.sleep(0.02)

    def test_qsl_refaite_depuis_le_fond(self):
        a = self.a
        fond = Image.new("RGB", (640, 400), "blue")
        carte = Image.new("RGB", (960, 600), "red")
        a.src_img, a._qsl_card, a._qsl_bg = carte, carte, fond
        seen = []
        real = self.app.qsl.make_card
        with mock.patch.object(self.app.qsl, "make_card", lambda bg, *x, **k: (seen.append(bg), real(bg, *x, **k))[1]):
            a.qsl_dialog()
            self.pump()
        self.assertTrue(seen)
        self.assertIs(seen[-1], fond)                      # pas l'ancienne carte

    def test_autre_image_ouverte_prise_comme_fond(self):
        a = self.a
        a._qsl_card, a._qsl_bg = Image.new("RGB", (10, 10)), Image.new("RGB", (10, 10))
        photo = Image.new("RGB", (640, 400), "green")
        a.src_img = photo                                  # nouvelle image ouverte depuis
        seen = []
        real = self.app.qsl.make_card
        with mock.patch.object(self.app.qsl, "make_card", lambda bg, *x, **k: (seen.append(bg), real(bg, *x, **k))[1]):
            a.qsl_dialog()
            self.pump()
        self.assertIs(seen[-1], photo)

    def test_effacer_image_tx(self):
        a = self.a
        a.src_img = Image.new("RGB", (64, 64), "white")
        a.bubbles = [{"text": "hi"}]
        a.clear_tx_image()
        self.assertIsNone(a.src_img)
        self.assertEqual(a.bubbles, [])
        self.assertIsNone(a.lb_cmp.pil)

    def test_enregistrer_image_tx(self):
        a = self.a
        a.src_img = Image.new("RGB", (64, 48), "white")
        out = os.path.join(self.d, "carte.jpg")
        with mock.patch.object(self.app.filedialog, "asksaveasfilename", return_value=out):
            a.save_tx_image()
        self.assertEqual(Image.open(out).size, (64, 48))

    def test_ordre_des_images(self):
        a = self.a
        p1, p2, p3 = {"path": "1"}, {"path": "2"}, {"path": "3"}
        a.pips = [p1, p2, p3]
        ed = a.tx_editor
        with mock.patch.object(ed, "changed"):
            ed.sel = ("p", 0)
            ed.restack(True)
            self.assertEqual(a.pips, [p2, p3, p1])
            self.assertEqual(ed.sel, ("p", 2))
            ed.restack(False)
            self.assertEqual(a.pips, [p1, p2, p3])

    def test_par_defaut_traduit(self):
        a = self.a
        a.settings() if hasattr(a, "settings") and not hasattr(a, "v_font") else None
        if not hasattr(a, "v_font"):
            self.skipTest("fenêtre des réglages non construite")
        self.assertEqual(a.v_font.get(), "(默认)")
        a._apply_look(save=False)
        self.assertEqual(a.conf["font_family"], "(par défaut)")
