"""1.95 : ambiances de fêtes et de saisons (Halloween, Noël, Hiver, Printemps, Été) et case
« Thème selon la saison » (décochée par défaut) — idée de F4GOP."""
import datetime
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import theme  # noqa: E402

D = datetime.date
NEW = ("Halloween", "Noël", "Hiver", "Printemps", "Été")


class Palettes(unittest.TestCase):
    def test_memes_couleurs_que_les_autres(self):
        keys = set(theme.MODERN["Sombre"])
        for n in NEW:
            self.assertTrue(keys <= set(theme.MODERN[n]), n)

    def test_lisibles(self):
        for n in NEW:
            P = theme.MODERN[n]
            self.assertGreaterEqual(theme._contrast(P["fg"], P["bg"]), 7, n)
            self.assertGreaterEqual(theme._contrast(P["fg"], P["field"]), 7, n)
            self.assertGreaterEqual(theme._contrast(P["accent_fg"], P["accent"]), 4.5, n)
            self.assertGreaterEqual(theme._contrast(P["bar_fg"], P["bar"]), 4.5, n)
            self.assertGreaterEqual(theme._contrast(P["top_fg"], P["top"]), 4.5, n)

    def test_traduits(self):
        import i18n
        import i18n_ru
        import i18n_zh
        for n in NEW + ("Thème selon la saison (Halloween, Noël)",):
            self.assertIn(n, {r[0] for r in i18n.T}, n)
            self.assertIn(n, i18n_zh.ZH, n)
            self.assertIn(n, i18n_ru.RU, n)


class Dates(unittest.TestCase):
    def test_halloween(self):
        self.assertIsNone(theme.season_theme(D(2026, 10, 19)))
        self.assertEqual(theme.season_theme(D(2026, 10, 20)), "Halloween")
        self.assertEqual(theme.season_theme(D(2026, 10, 31)), "Halloween")
        self.assertIsNone(theme.season_theme(D(2026, 11, 1)))

    def test_noel_a_cheval_sur_deux_annees(self):
        self.assertIsNone(theme.season_theme(D(2026, 11, 30)))
        self.assertEqual(theme.season_theme(D(2026, 12, 1)), "Noël")
        self.assertEqual(theme.season_theme(D(2026, 12, 25)), "Noël")
        self.assertEqual(theme.season_theme(D(2027, 1, 6)), "Noël")
        self.assertIsNone(theme.season_theme(D(2027, 1, 7)))
        self.assertIsNone(theme.season_theme(D(2027, 7, 14)))


class Appli(unittest.TestCase):
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

    def jour(self, day):
        class FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return day
        return mock.patch.object(self.app.datetime, "date", FakeDate)

    def regle(self, saison, moderne, amb):
        """Comme dans la fenêtre des Réglages (ses cases et listes font foi quand elles existent)."""
        import i18n
        a = self.a
        a.conf.update(season_theme=saison, look_style="moderne" if moderne else "classique", modern_theme=amb)
        if hasattr(a, "v_lookstyle"):
            a.v_lookstyle.set(i18n.tr("Moderne") if moderne else i18n.tr("Classique (EasyPal)"))
            a.v_modern.set(i18n.tr(amb))
        if hasattr(a, "v_season"):
            a.v_season.set(saison)

    def test_decochee_par_defaut(self):
        self.assertFalse(self.app.DEFAULTS["season_theme"])
        with self.jour(D(2026, 10, 31)):
            self.a._apply_look(save=False)
        self.assertIsNone(self.a.look.modern)                       # Classique, comme avant

    def test_fete_puis_retour_au_choix(self):
        a = self.a
        self.regle(True, False, "Clair")
        with self.jour(D(2026, 12, 24)):
            a._apply_look(save=False)
        self.assertEqual(a.look.modern, "Noël")
        self.assertEqual(a.look.palette()["accent"], theme.MODERN["Noël"]["accent"])
        self.assertEqual(a.conf["look_style"], "classique")          # le choix enregistré ne change pas
        self.assertEqual(a.conf["modern_theme"], "Clair")
        with self.jour(D(2027, 2, 1)):
            a._apply_look(save=False)
        self.assertIsNone(a.look.modern)                            # fête finie : Classique revient

    def test_ambiance_choisie_a_la_main(self):
        a = self.a
        self.regle(False, True, "Printemps")
        a._apply_look(save=False)
        self.assertEqual(a.look.modern, "Printemps")


if __name__ == "__main__":
    unittest.main()
