"""2.06 : option « Boutons arrondis (style Moderne) », décochée par défaut. Fond arrondi dessiné en image pour la
grille de gauche (couleurs d'état gardées) et bordure arrondie pour les boutons ttk ; aucun changement de place,
pas de boucle de redimensionnement ; tout revient comme avant quand on décoche."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Arrondis(unittest.TestCase):
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
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "look_style": "moderne",
                       "modern_theme": "Néon bleu", "net_on": False}, f)
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

    def pump(self, n=20):
        for _ in range(n):
            self.a.update()

    def sizes(self):
        return {k: (b.winfo_width(), b.winfo_height()) for k, b in self.a.gbtn.items()}

    def set_round(self, on):
        self.a.conf["round_btn"] = on
        self.a._apply_look(save=False)
        self.pump()

    def test_decochee_par_defaut(self):
        self.assertFalse(self.app.DEFAULTS["round_btn"])
        self.assertEqual(str(self.a.gbtn["fix"].cget("image")), "")

    def test_aller_retour_meme_place(self):
        a = self.a
        avant = self.sizes()
        self.set_round(True)
        b = a.gbtn["fix"]
        self.assertNotEqual(str(b.cget("image")), "")
        self.assertEqual(self.sizes(), avant)                          # aucune place en plus ou en moins
        self.assertTrue(any("HFR" in str(e) for e in [a.look.style.layout("TButton")]))
        self.set_round(False)
        self.assertEqual(str(b.cget("image")), "")
        self.assertEqual(self.sizes(), avant)
        self.assertFalse("HFR" in str(a.look.style.layout("TButton")))

    def test_pas_de_boucle(self):
        a = self.a
        n = [0]
        orig = a._round_grid
        with mock.patch.object(a, "_round_grid", lambda *x, **k: (n.__setitem__(0, n[0] + 1), orig(*x, **k))):
            self.set_round(True)
            self.pump(60)
            stable = n[0]
            self.pump(100)                                             # plus rien ne bouge
        self.assertEqual(n[0], stable)
        self.assertLess(stable, 6 * len(a.gbtn))

    def test_couleur_d_etat(self):
        a = self.a
        self.set_round(True)
        b = a.gbtn["tx"]
        im0 = str(b.cget("image"))
        a._btn_color(b, "tx")                                          # émission : rouge
        self.pump(3)
        self.assertNotEqual(str(b.cget("image")), im0)
        self.assertEqual(b._hf_fill, a.look.palette()["bad"])

    def test_style_classique_non_concerne(self):
        a = self.a
        a.conf.update(round_btn=True, look_style="classique")
        if hasattr(a, "v_lookstyle"):
            import i18n
            a.v_lookstyle.set(i18n.tr("Classique (EasyPal)"))
        a._apply_look(save=False)
        self.pump()
        self.assertFalse(a._round_on())
        self.assertEqual(str(a.gbtn["fix"].cget("image")), "")


if __name__ == "__main__":
    unittest.main()
