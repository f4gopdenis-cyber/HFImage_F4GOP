"""1.28 : fenêtre « Sites des stations » (remplace Digi-Sites)."""
import http.server
import io
import os
import sys
import threading
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import hybrid  # noqa: E402
import sites  # noqa: E402
from PIL import Image  # noqa: E402


def jpeg(color):
    b = io.BytesIO()
    Image.new("RGB", (320, 240), color).save(b, "JPEG")
    return b.getvalue()


class Serveur(http.server.BaseHTTPRequestHandler):
    data = jpeg((200, 0, 0))
    hits = []

    def do_GET(self):
        Serveur.hits.append(self.headers.get("If-None-Match"))
        if self.headers.get("If-None-Match") == '"v1"':
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("ETag", '"v1"')
        self.send_header("Last-Modified", "Fri, 23 Oct 2026 09:28:00 GMT")
        self.send_header("Content-Length", str(len(self.data)))
        self.end_headers()
        self.wfile.write(self.data)

    def log_message(self, *a):
        pass


class Sites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), Serveur)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/image1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_securite(self):
        with self.assertRaises(hybrid.Refused):              # adresse locale : refusée
            sites.fetch(self.url)
        self.assertFalse(sites.valid_url("file:///etc/passwd"))
        self.assertFalse(sites.valid_url("ftp://x/image1"))
        self.assertTrue(sites.valid_url("https://www.qsl.net/f4gop/image1"))

    def test_lecture_conditionnelle(self):
        with mock.patch.object(hybrid, "_check_public_url", lambda u: None):
            data, et, lm = sites.fetch(self.url)
            self.assertEqual(data, Serveur.data)
            again, et2, lm2 = sites.fetch(self.url, et, lm)
        self.assertIsNone(again)                              # inchangé : rien retéléchargé
        self.assertEqual((et2, lm2), (et, lm))
        self.assertRegex(sites.when_text(lm), r"\d\d:\d\d")

    def test_fenetre(self):
        try:
            import app
            import tkinter as tk
            root = tk.Tk()
        except Exception as e:
            self.skipTest(str(e))
        fake = types.SimpleNamespace(
            online={"a": {"call": "F4EEH", "site": self.url, "loc": "JN18EU"},
                    "b": {"call": "G4GIM"}, "c": {"call": "X1", "site": "file:///etc"}},
            conf={"sites_extra": [{"call": "VK6NJP", "url": "https://crac.50webs.com/easypal/image1"}]},
            _translate_ui=lambda w: None, _label=lambda c: c, _distance_to=lambda c: 312.0 if c == "F4EEH" else None,
            _save_conf_file=lambda: None)
        fake.ui = lambda fn, *a: root.after(0, fn, *a)
        w = sites.SitesWindow.__new__(sites.SitesWindow)
        tk.Toplevel.__init__(w, root)
        w.app = fake
        sts = sites.SitesWindow.stations(w)
        self.assertEqual([s[0] for s in sts], ["F4EEH", "VK6NJP"])     # sans site ou adresse refusée : absent
        root.destroy()


if __name__ == "__main__":
    unittest.main()
