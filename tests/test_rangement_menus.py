"""Version 0.97 : onglet Simulation caché d'office, menu Effacer dans Fichiers,
« Décoder et analyser un fichier WAV » en une seule commande."""
import os
import sys
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Rangement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import app
            import i18n
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        cls.home = mock.patch.dict(os.environ, {"HOME": tempfile.mkdtemp(), "APPDATA": tempfile.mkdtemp(),
                                                "LOCALAPPDATA": tempfile.mkdtemp()})
        cls.home.start()
        i18n.set_lang("fr")
        cls.p = [mock.patch.object(i18n, "detect_lang", lambda: "fr"),
                 mock.patch.object(app.App, "_licence_first_run", lambda self: None),
                 mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: None)]
        for p in cls.p:
            p.start()
        try:
            cls.a = app.App()
        except Exception as e:
            raise unittest.SkipTest(f"fenêtre principale impossible ici : {e}")
        cls.a.update()

    @classmethod
    def tearDownClass(cls):
        cls.a.destroy()
        for p in cls.p:
            p.stop()
        cls.home.stop()

    def tabs(self):
        nb = self.a.nb
        return [nb.tab(t, "text").strip() for t in nb.tabs() if nb.tab(t, "state") != "hidden"]

    def test_simulation_cachee_puis_affichee(self):
        self.assertNotIn("Simulation", self.tabs())
        self.a.v_simtab.set(True)
        self.a._sim_tab_toggle()
        self.assertIn("Simulation", self.tabs())
        self.a.v_simtab.set(False)
        self.a._sim_tab_toggle()
        self.assertNotIn("Simulation", self.tabs())

    def test_menus(self):
        m = self.a.nametowidget(self.a.cget("menu"))
        top = [m.entrycget(i, "label") for i in range(1, m.index("end") + 1)]
        self.assertNotIn("Effacer", top)
        f = self.a.nametowidget(m.entrycget(m.index("Fichiers"), "menu"))
        labels = [f.entrycget(i, "label") for i in range(f.index("end") + 1) if f.type(i) != "separator"]
        self.assertIn("Effacer", labels)
        self.assertIn("Décoder et analyser un fichier WAV…", labels)
        self.assertNotIn("Analyser un enregistrement WAV…", labels)

    def test_decoder_ouvre_l_analyse(self):
        p = os.path.join(tempfile.mkdtemp(), "x.wav")
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(np.zeros(8000, np.int16).tobytes())
        seen = []
        with mock.patch.object(self.a, "analyze_wav", seen.append):
            self.a.decode_wav(p)
        self.assertEqual(seen, [p])


if __name__ == "__main__":
    unittest.main()
