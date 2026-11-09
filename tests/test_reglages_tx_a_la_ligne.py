"""2.27 (F4IUJ) : petit écran : les réglages de l'onglet TX passent à la ligne au lieu de sortir de la fenêtre."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Flow(unittest.TestCase):
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
            json.dump({"callsign": "F4IUJ", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
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
        self.a = None
        gc.collect()
        self.p.stop()

    def layout(self, width):
        a = self.a
        a.geometry(f"{width}x700")
        a.show_tab("tx")
        for _ in range(25):
            a.update()
        return a._flow_rows

    def test_tout_reste_visible(self):
        rows = self.layout(900)
        for r in rows:
            W = r.winfo_width()
            for u in r._flow_units:
                for w, _l, _r in u:
                    self.assertLessEqual(w.winfo_x() + w.winfo_width(), W + 2, str(w))

    def test_plus_de_lignes_quand_c_est_etroit(self):
        large = sum(r.winfo_height() for r in self.layout(1650))
        etroit = sum(r.winfo_height() for r in self.layout(900))
        self.assertGreater(etroit, large)

    def test_etiquette_collee_a_sa_liste(self):
        rows = self.layout(900)
        for r in rows:
            for u in r._flow_units:
                if len(u) > 1:
                    ys = {w.winfo_y() // 10 for w, _l, _r in u}
                    self.assertLessEqual(len(ys), 2)            # même ligne (centrage vertical à part)
