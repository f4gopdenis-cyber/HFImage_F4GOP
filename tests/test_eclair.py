"""Hybride éclair (version 0.71) : trame DATAC0 + lien par le serveur de présence.

Lancer depuis la racine du dépôt :  python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import presence  # noqa: E402
import protocol  # noqa: E402

DATA = bytes(range(256)) * 200
URL = "https://f4gop.example.org/hfimage/F4GOP_20261018_141000.avif"


class Trame(unittest.TestCase):
    def test_aller_retour(self):
        f = protocol.flash_frame(0x1234, DATA, "avif")
        self.assertLessEqual(len(f), 14)                    # une trame DATAC0
        d = protocol.parse_flash(f.ljust(14, b"\0"))
        self.assertEqual(d, {"id": 0x1234, "key": protocol.flash_key(DATA), "size": len(DATA), "fmt": "avif"})

    def test_autres_trames_refusees(self):
        self.assertIsNone(protocol.parse_flash(protocol.qrv_frame("F4GOP", "IN98QR")))
        self.assertIsNone(protocol.parse_flash(b"\x82" + b"\0" * 13))   # taille nulle
        self.assertIsNone(protocol.parse_flash(b"\x82"))

    def test_anciennes_versions_ignorent(self):
        f = protocol.flash_frame(7, DATA, "avif").ljust(14, b"\0")
        self.assertIsNone(protocol.Receiver("F5ABC").feed(f))
        self.assertIsNone(protocol.parse_hybrid(f))


class Serveur(unittest.TestCase):
    def setUp(self):
        self.p = presence.Presence("h", 1, None, None, None)
        self.key = protocol.flash_key(DATA)
        self.good = {"call": "f4gop/p", "url": URL, "size": len(DATA), "crc": zlib.crc32(DATA),
                     "fmt": "avif", "id": 7}

    def test_lien_valide(self):
        self.p._store_flash(self.key, self.good)
        r = self.p.get_flash(self.key)
        self.assertEqual((r["call"], r["url"], r["size"]), ("F4GOP/P", URL, len(DATA)))

    def test_liens_refuses(self):
        bad = [("ZZ", self.good), (self.key, dict(self.good, url="ftp://x/y")),
               (self.key, dict(self.good, url="javascript:alert(1)")),
               (self.key, dict(self.good, size=presence.MAX_SIZE + 1)), (self.key, dict(self.good, size=0)),
               (self.key, dict(self.good, crc="abc")), (self.key, "pas un dict"),
               (self.key, {k: v for k, v in self.good.items() if k != "size"})]
        for key, d in bad:
            self.p._store_flash(key, d)
        self.assertEqual(self.p.flash, {})

    def test_indicatif_nettoye(self):
        self.p._store_flash(self.key, dict(self.good, call="..\\..\\x<b>"))
        self.assertEqual(self.p.get_flash(self.key)["call"], "XB")

    def test_cache_limite(self):
        for i in range(presence.FLASH_MAX + 50):
            self.p._store_flash(f"{i:012x}", self.good)
        self.assertEqual(len(self.p.flash), presence.FLASH_MAX)


class Modem(unittest.TestCase):
    """Bout à bout par le vrai modem (sauté si libcodec2 n'a pas DATAC1X, utilisé par RxEngine)."""

    def test_annonce_eclair_decodee(self):
        import numpy as np

        import engine
        try:
            rx_holder = []
            rx = engine.RxEngine("F5ABC", tempfile.mkdtemp(), on_hybrid=lambda h, m: rx_holder.append((h, m)))
        except RuntimeError as e:
            self.skipTest(str(e))
        tx = engine.HybridTransmission(DATA, "avif", "F4GOP", URL, flash=True)
        self.assertEqual(tx.mode, "DATAC0")
        self.assertLess(tx.estimate_s(), 4.0)
        a = np.concatenate([np.zeros(4000, np.float32), tx.audio().astype(np.float32), np.zeros(8000, np.float32)])
        for i in range(0, len(a), 800):
            rx.process(a[i:i + 800])
        self.assertEqual(len(rx_holder), 1)                  # 3 copies, une seule annonce
        h, mode = rx_holder[0]
        self.assertTrue(h["flash"])
        self.assertEqual((h["key"], h["size"], h["id"], mode), (tx.key, len(DATA), tx.image_id, "DATAC0"))


if __name__ == "__main__":
    unittest.main()
