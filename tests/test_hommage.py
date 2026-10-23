"""1.33 : drapeau australien et hommage à VK4AES dans la barre du bas."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import flag  # noqa: E402
import i18n  # noqa: E402


class Hommage(unittest.TestCase):
    def test_drapeau(self):
        im = flag.australia(24, 12)
        self.assertEqual(im.size, (24, 12))
        big = flag.australia(200, 100)
        self.assertGreater(big.getpixel((150, 85))[2], 80)          # fond bleu
        self.assertGreater(big.getpixel((50, 25))[0], 150)          # croix rouge au centre de l'Union Jack

    def test_traduction(self):
        try:
            i18n.set_lang("en")
            self.assertEqual(i18n.tr("En hommage à VK4AES"), "In memory of VK4AES")
        finally:
            i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
