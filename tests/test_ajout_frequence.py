"""2.42 (demande de F4GOP) : ajouter une fréquence au menu « Fréquence ▾ » en un clic
(fréquence du poste, ou fréquence tapée dans « Autre fréquence… » avec « Ajouter à la liste »)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class AjoutFrequence(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = self.conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr"}, f)
        gc.collect()
        self.p = mock.patch.object(app, "CONF_PATH", conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.qsy = []
        self.a._qsy = lambda hz, side=None: self.qsy.append((hz, side))

    def tearDown(self):
        self.a.destroy()
        self.p.stop()

    def labels(self):
        import tkinter as tk
        m = tk.Menu(self.a, tearoff=0)
        self.a._fill_qsy_menu(m)
        out = {}
        for i in range(m.index("end") + 1):
            if m.type(i) != "separator":
                out[m.entrycget(i, "label")] = (m, i)
        return out

    def test_frequence_du_poste(self):
        a = self.a
        a.rig_freq, a.rig_mode = 18_160_000, "USB"
        lab = next(k for k in self.labels() if k.startswith("Ajouter la fréquence du poste"))
        self.assertIn("18.160 MHz USB", lab)
        m, i = self.labels()[lab]
        self.assertEqual(m.entrycget(i, "state"), "normal")
        m.invoke(i)
        self.assertIn((18_160_000, "USB"), a._freq_presets())
        self.assertIn([18_160_000, "USB"], json.load(open(self.conf))["freq_presets"])     # gardée
        hz = [f for f, _s in a._freq_presets()]
        self.assertEqual(hz, sorted(hz))                                                    # à sa place
        m, i = self.labels()[lab]
        self.assertEqual(m.entrycget(i, "state"), "disabled")                               # déjà là
        self.assertFalse(a._freq_add(18_160_400))                                           # pas de doublon

    def test_sans_cat(self):
        self.a.rig_freq = None
        m, i = self.labels()["Ajouter la fréquence du poste"]
        self.assertEqual(m.entrycget(i, "state"), "disabled")

    def test_lsb_sous_10_mhz(self):
        a = self.a
        a.rig_freq, a.rig_mode = 3_735_000, None
        self.assertEqual(a._rig_freq_side(), (3_735_000, "LSB"))
        a.rig_mode = "USB-D"
        self.assertEqual(a._rig_freq_side(), (3_735_000, "USB"))

    def test_autre_frequence_avec_ajout(self):
        a = self.a
        self.assertTrue(a._qsy_go("24.950", add=True))
        self.assertEqual(self.qsy, [(24_950_000, None)])
        self.assertIn((24_950_000, "USB"), a._freq_presets())
        self.assertTrue(a._qsy_go("10.140", add=False))
        self.assertNotIn(10_140_000, [f for f, _s in a._freq_presets()])
        with mock.patch.object(__import__("app").messagebox, "showerror") as err:
            self.assertFalse(a._qsy_go("abc", add=True))
            err.assert_called_once()

    def test_fenetre_autre_frequence(self):
        a = self.a
        a.rig_freq = 7_058_000
        w = a._qsy_ask()
        a.update()
        import tkinter as tk
        from tkinter import ttk

        def walk(x):
            yield x
            for c in x.winfo_children():
                yield from walk(c)
        cb = next(x for x in walk(w) if isinstance(x, ttk.Checkbutton))
        self.assertEqual(str(cb.cget("text")), "Ajouter à la liste")
        ent = next(x for x in walk(w) if isinstance(x, ttk.Entry))
        self.assertEqual(ent.get(), "7.058")
        w.destroy()
        self.assertIsInstance(w, tk.Toplevel)


if __name__ == "__main__":
    unittest.main()
