"""1.54 : style « Moderne » (plat, 3 ambiances, barre du haut) à côté du style Classique (EasyPal),
réversible à tout moment sans redémarrer."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import theme  # noqa: E402


class Palette(unittest.TestCase):
    def test_roles(self):
        P = theme.MODERN["Sombre"]
        self.assertEqual(theme.modern_color(P, "#33d633", "background"), P["bar"])     # vert EasyPal
        self.assertEqual(theme.modern_color(P, "#ffffff", "background"), P["field"])
        self.assertEqual(theme.modern_color(P, "#000000", "background"), "#000000")    # image, waterfall
        self.assertEqual(theme.modern_color(P, "#000000", "foreground"), P["fg"])
        self.assertEqual(theme.modern_color(P, "#ffffff", "background", cls="Button"), P["button"])
        self.assertEqual(theme.modern_color(P, "#062e06", "foreground", bg_role="bar"), P["bar_fg"])
        red = theme.modern_color(P, "#c01818", "foreground")
        self.assertNotEqual(red, P["fg"])                                    # couleur d'alerte gardée

    def test_ambiances(self):
        self.assertEqual(set(theme.MODERN), {"Vert EasyPal", "Sombre", "Clair", "Vert radio"})
        self.assertEqual(list(theme.MODERN)[0], "Vert EasyPal")              # en tête de liste
        P = theme.MODERN["Vert EasyPal"]
        self.assertEqual(P["bar"], "#33d633")                               # le vert EasyPal d'origine

    def test_par_defaut(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.assertEqual(app.DEFAULTS["modern_theme"], "Vert EasyPal")
        self.assertEqual(app.DEFAULTS["look_style"], "classique")


class Appli(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.appmod = app
        d = tempfile.mkdtemp()
        self.conf = os.path.join(d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr"}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def style(self, moderne, amb="Sombre"):
        a = self.a
        import i18n
        a.conf["look_style"], a.conf["modern_theme"] = ("moderne" if moderne else "classique"), amb
        if hasattr(a, "v_lookstyle"):                         # réglages ouverts : leurs listes font foi
            a.v_lookstyle.set(i18n.tr("Moderne") if moderne else i18n.tr("Classique (EasyPal)"))
            a.v_modern.set(i18n.tr(amb))
        a._apply_look(save=False)
        a.update()

    def test_aller_retour(self):
        a = self.a
        b = a.gbtn["fix"] if "fix" in a.gbtn else list(a.gbtn.values())[1]
        classic = (str(b.cget("relief")), str(b.cget("bg")), str(a.cget("bg")))
        self.assertFalse(a.topbar.winfo_manager())                     # Classique : pas de barre du haut
        self.style(True, "Clair")
        P = theme.MODERN["Clair"]
        self.assertEqual(str(b.cget("relief")), "flat")
        self.assertEqual(str(b.cget("bg")), P["button"])
        self.assertTrue(a.topbar.winfo_manager())
        a._topbar_update()
        self.assertEqual(a.tb["call"].cget("text"), "F4GOP")
        self.style(True, "Sombre")
        self.assertEqual(str(b.cget("bg")), theme.MODERN["Sombre"]["button"])
        self.style(False)
        self.assertEqual((str(b.cget("relief")), str(b.cget("bg")), str(a.cget("bg"))), classic)
        self.assertFalse(a.topbar.winfo_manager())

    def test_tuiles_avec_icones(self):
        # 1.56 : style Moderne -> tuiles avec icône ; Classique -> boutons texte comme avant
        a = self.a
        b = a.gbtn["fix"]
        self.assertEqual(str(b.cget("image")), "")
        self.style(True, "Vert EasyPal")
        self.assertNotEqual(str(b.cget("image")), "")
        self.assertEqual(str(b.cget("compound")), "top")
        self.assertEqual(str(a.gbtn["tx"].cget("bg")), theme.MODERN["Vert EasyPal"]["accent"])
        self.style(False)
        self.assertEqual(str(b.cget("image")), "")
        self.assertEqual(str(b.cget("compound")), "none")

    def test_icones(self):
        import icons
        for n in icons.NAMES:
            im = icons.icon(n, 18, "#123456")
            self.assertEqual(im.size, (18, 18))
            self.assertGreater(im.getchannel("A").getextrema()[1], 100, n)

    def test_bouton_emission_en_moderne(self):
        a = self.a
        self.style(True, "Sombre")
        a._btn_color(a.gbtn["tx"], "tx")
        self.assertEqual(str(a.gbtn["tx"].cget("bg")), theme.MODERN["Sombre"]["bad"])
        a._btn_color(a.gbtn["tx"], "off")
        self.assertEqual(str(a.gbtn["tx"].cget("bg")), theme.MODERN["Sombre"]["accent"])    # tuile principale


if __name__ == "__main__":
    unittest.main()
