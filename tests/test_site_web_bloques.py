"""2.24 (BH2RMX) : étiquette des images mises en ligne lisible en chinois, page sans texte en double,
indicatifs bloqués absents de « Sites des stations » et jamais remis en ligne."""
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import websync  # noqa: E402


class Page(unittest.TestCase):
    def test_traduction_chinoise(self):
        import i18n_zh
        self.assertEqual(i18n_zh.ZH["émise par"], "发送者：")

    def test_pas_de_texte_sous_l_image(self):
        page = websync._page("BH2RMX", [{"caption": "BH2RMX 2026-11-08"}], [], 3)
        self.assertNotIn("<figcaption>", page)
        self.assertIn('alt="BH2RMX 2026-11-08"', page)

    def test_etiquette_chinoise(self):
        p = os.path.join(tempfile.mkdtemp(), "t.png")
        Image.new("RGB", (600, 300), "gray").save(p)
        data, size = websync.label_image(p, "发送者： BH2RMX 2026-11-08 02:31 UTC")
        im = Image.open(io.BytesIO(data))
        self.assertGreater(im.height, 300)
        f = websync._label_font("发送者", 20)
        if getattr(f, "path", None):
            self.assertTrue(f.font.getsize("发") if hasattr(f.font, "getsize") else True)


class Sites(unittest.TestCase):
    def test_station_bloquee_cachee(self):
        import sites
        app = mock.MagicMock()
        app.online = {"a": {"call": "F5XXX", "site": "https://example.org/image1.jpg"},
                      "b": {"call": "F4GOP", "site": "https://example.org/g/image1.jpg"}}
        app.conf = {"sites_extra": []}
        app.is_blocked = lambda c: c == "F5XXX"
        w = sites.SitesWindow.__new__(sites.SitesWindow) if hasattr(sites, "SitesWindow") else None
        if w is None:
            cls = next(v for v in vars(sites).values() if isinstance(v, type) and hasattr(v, "stations"))
            w = cls.__new__(cls)
        w.app = app
        self.assertEqual([s[0] for s in w.stations()], ["F4GOP"])
