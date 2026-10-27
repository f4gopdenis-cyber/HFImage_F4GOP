"""Version 1.76 : site web sur un autre serveur FTP que le mode hybride (VK6NJP : mur du club)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class AutreServeur(unittest.TestCase):
    def stub(self, conf):
        try:
            import app
            import hybrid
        except ImportError as e:
            self.skipTest(str(e))
        s = mock.Mock()
        s.conf = conf
        s.mycall.return_value = "VK6NJP"
        s._hyb_cfg.return_value = {"host": "ftp.qsl.net", "port": 21, "user": "vk6njp", "password": "h",
                                   "dir": "hfimage", "tls": False, "url": "https://www.qsl.net/vk6njp/hfimage/"}
        return app.App._web_cfg(s), hybrid

    def test_serveur_du_mode_hybride_par_defaut(self):
        c, _ = self.stub({"web_dir": "easypal", "web_url": "http://x/easypal/"})
        self.assertEqual((c["host"], c["user"], c["dir"], c["url"]),
                         ("ftp.qsl.net", "vk6njp", "easypal", "http://x/easypal/"))

    def test_autre_serveur(self):
        try:
            import hybrid
        except ImportError as e:
            self.skipTest(str(e))
        c, _ = self.stub({"web_own": True, "web_host": "crac.50webs.com", "web_port": 2121,
                          "web_user": "vk6njp_crac", "web_pass": hybrid.protect("secret"), "web_tls": True,
                          "web_dir": "easypal", "web_url": "http://vk6njp.50webs.com/easypal/"})
        self.assertEqual((c["host"], c["port"], c["user"], c["password"], c["tls"], c["dir"]),
                         ("crac.50webs.com", 2121, "vk6njp_crac", "secret", True, "easypal"))


if __name__ == "__main__":
    unittest.main()
