"""Version 1.03 : aide au réglage du serveur hybride (cas de VK6NJP : port 22, lien « ftp.qsl.net »)."""
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import hybrid  # noqa: E402

CFG = {"host": "ftp.qsl.net", "port": 22, "user": "WASSTV", "password": "x", "dir": "easypal",
       "url": "ftp.qsl.net", "tls": True}


class FakeFTP:
    log = []

    def __init__(self, timeout=None):
        pass

    def connect(self, host, port):
        FakeFTP.log.append(("connect", host, port))

    def login(self, u, p):
        pass

    def prot_p(self):
        pass

    def cwd(self, d):
        FakeFTP.log.append(("cwd", d))

    def mkd(self, d):
        pass

    def storbinary(self, cmd, f, blocksize=8192, callback=None):
        FakeFTP.log.append(("stor", cmd))

    def delete(self, n):
        FakeFTP.log.append(("delete", n))

    def quit(self):
        pass

    def close(self):
        pass


class Aide(unittest.TestCase):
    def test_port_22(self):
        with self.assertRaises(RuntimeError) as c:
            hybrid._ftp_connect(dict(CFG))
        self.assertIn("port 21", str(c.exception))

    def test_lien_suggere_qsl(self):
        self.assertFalse(hybrid.has_public_url(CFG))
        self.assertEqual(hybrid.suggest_public_url(CFG), "https://www.qsl.net/wasstv/easypal/")
        self.assertIsNone(hybrid.suggest_public_url(dict(CFG, host="ftp.example.com")))

    def test_ftp_seul(self):
        FakeFTP.log.clear()
        with mock.patch.object(hybrid.ftplib, "FTP", FakeFTP), mock.patch.object(hybrid.ftplib, "FTP_TLS", FakeFTP):
            hybrid.test_ftp(dict(CFG, port=21))
        kinds = [x[0] for x in FakeFTP.log]
        self.assertEqual(kinds[:3], ["connect", "cwd", "stor"])
        self.assertIn("delete", kinds)

    def test_fenetre_propose_le_lien(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        asked, tested = [], []
        url = types.SimpleNamespace(v="", set=lambda v: setattr(url, "v", v), get=lambda: url.v)
        s = types.SimpleNamespace(log=lambda m: None, v_hurl=url, save_conf=lambda quiet=False: None,
                                  test_hybrid=lambda: tested.append(url.v))
        with mock.patch.object(app.messagebox, "askyesno", lambda t, m, **k: asked.append(m) or True):
            app.App._ftp_only_ok(s, dict(CFG, port=21))
        self.assertIn("EasyPal", asked[0])
        self.assertIn("https://www.qsl.net/wasstv/easypal/", asked[0])
        self.assertEqual(tested, ["https://www.qsl.net/wasstv/easypal/"])


if __name__ == "__main__":
    unittest.main()
