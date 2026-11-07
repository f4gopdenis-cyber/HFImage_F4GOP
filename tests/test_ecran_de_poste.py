"""2.18 : barre du haut « écran de poste » (fréquence 7.058.000 dans un afficheur, indicatif en pastille)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import topdisplay  # noqa: E402


class Ecran(unittest.TestCase):
    def test_format_frequence(self):
        self.assertEqual(topdisplay.freq_text(7_058_000), "7.058.000")
        self.assertEqual(topdisplay.freq_text(14_233_500), "14.233.500")
        self.assertEqual(topdisplay.freq_text(3_733_000), "3.733.000")

    def test_largeur_fixe(self):
        a = topdisplay.lcd(7_058_000, "LSB-DATA1", "40 m", (42, 100, 200), 16)
        b = topdisplay.lcd(14_233_000, "USB-DATA1", "20 m", (42, 100, 200), 16)
        if a is None:
            self.skipTest("aucune police")
        self.assertEqual(a.size[0], b.size[0])               # la barre ne bouge pas quand on change de bande

    def test_sans_frequence(self):
        im = topdisplay.lcd(None, "", "", (42, 100, 200), 16, "Frequency ▾")
        if im is None:
            self.skipTest("aucune police")
        self.assertGreater(im.size[0], 50)

    def test_pastille(self):
        im = topdisplay.pill("F4GOP", (255, 216, 74), (6, 16, 42), 16)
        if im is None:
            self.skipTest("aucune police")
        self.assertGreater(im.size[0], im.size[1])
