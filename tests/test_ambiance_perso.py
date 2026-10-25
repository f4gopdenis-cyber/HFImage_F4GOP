"""Version 1.63 : style Moderne, ambiance « Personnalisée » tirée d'une seule couleur."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    import theme  # noqa: E402
except ImportError:                                    # pas de tkinter
    theme = None


@unittest.skipIf(theme is None, "tkinter absent")
class AmbiancePerso(unittest.TestCase):
    COLORS = ("#3a8ee6", "#e8762c", "#1b2a49", "#f2d14b", "#33d633", "#ffffff", "#000000", "#808080", "pas une couleur")

    def test_palette_complete_et_lisible(self):
        keys = set(theme.MODERN["Vert EasyPal"])
        for c in self.COLORS:
            P = theme.modern_custom(c)
            self.assertTrue(keys <= set(P), c)
            self.assertGreaterEqual(theme._contrast(P["accent"], P["accent_fg"]), 4.5, c)
            self.assertGreaterEqual(theme._contrast(P["bar"], P["bar_fg"]), 4.5, c)
            self.assertGreaterEqual(theme._contrast(P["bg"], P["fg"]), 7, c)
            self.assertGreaterEqual(theme._contrast(P["field"], P["fg"]), 7, c)

    def test_barre_dans_la_couleur_choisie(self):
        self.assertEqual(theme.modern_custom("#e8762c")["bar"], "#e8762c")
        self.assertEqual(theme.modern_custom("#f2d14b")["bar_fg"], "#111111")     # jaune : texte noir
        self.assertEqual(theme.modern_custom("#1b2a49")["bar_fg"], "#ffffff")     # bleu nuit : texte blanc


if __name__ == "__main__":
    unittest.main()
