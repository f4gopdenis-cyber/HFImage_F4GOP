"""Version 1.70 : menu Infos → « Soutenir HFImage (don)… » ouvre la page PayPal de F4GOP."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Don(unittest.TestCase):
    def test_lien(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        self.assertEqual(app.DONATE_URL, "https://www.paypal.com/paypalme/F4GOP")

    def test_traduit(self):
        import i18n
        i18n.set_lang("en")
        try:
            self.assertEqual(i18n.tr("Soutenir HFImage (don)…"), "Support HFImage (donation)…")
        finally:
            i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
