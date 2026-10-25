"""Version 1.64 : HTTPS avec la liste certifi en plus des certificats du système ; FT-991A trouvé."""
import os
import ssl
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import netssl  # noqa: E402
import radio  # noqa: E402


class Certificats(unittest.TestCase):
    def setUp(self):
        netssl._CTX = None

    def test_certifi_ajoute(self):
        try:
            import certifi
        except ImportError as e:
            self.skipTest(str(e))
        loaded = []
        real = ssl.SSLContext.load_verify_locations

        def spy(self, cafile=None, *a, **k):
            loaded.append(cafile)
            return real(self, cafile, *a, **k)
        with mock.patch.object(ssl.SSLContext, "load_verify_locations", spy):
            ctx = netssl.context()
        self.assertIn(certifi.where(), loaded)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)       # vérification gardée
        self.assertTrue(ctx.check_hostname)

    def test_sans_certifi(self):
        with mock.patch.dict(sys.modules, {"certifi": None}):
            ctx = netssl.context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_message_clair(self):
        e = OSError("<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                    "unable to get local issuer certificate (_ssl.c:1010)>")
        self.assertIn("date et l'heure", netssl.explain(e))
        self.assertEqual(netssl.explain(OSError("timed out")), "timed out")

    def test_urlopen_passe_le_contexte(self):
        got = {}
        with mock.patch.object(netssl.urllib.request, "urlopen",
                               lambda req, timeout, context: got.update(c=context, t=timeout)):
            netssl.urlopen("https://example.org", 7)
        self.assertIs(got["c"], netssl.context())
        self.assertEqual(got["t"], 7)


class Ft991a(unittest.TestCase):
    def test_libelle_et_recherche(self):
        self.assertEqual(radio.rig_label("hamlib:1035"), "Yaesu FT-991 / FT-991A")
        found = [k for k in radio.rig_keys() if "991a" in radio.rig_label(k).lower()]
        self.assertEqual(found, ["hamlib:1035"])
        self.assertEqual(radio.rig_entry("hamlib:1035")["kind"], "hamlib")


if __name__ == "__main__":
    unittest.main()
