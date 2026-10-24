"""1.42 : vérification des mises à jour quand l'API GitHub refuse (« 403 rate limit exceeded ») :
secours par la page « dernière version » du site, sans limite."""
import http.server
import os
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import updater  # noqa: E402
import i18n  # noqa: E402

SIZE = 12345


class Faux(http.server.BaseHTTPRequestHandler):
    api_code = 403
    asset_ok = True

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path
        if p.startswith("/api"):
            self.send_response(self.api_code)
            self.end_headers()
            self.wfile.write(b'{"message":"API rate limit exceeded"}')
        elif p == "/releases/latest":
            self.send_response(302)
            self.send_header("Location", "/releases/tag/v9.87")
            self.end_headers()
        elif p == "/releases/tag/v9.87":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html>page</html>")
        elif p.startswith("/download/v9.87/") and self.asset_ok:
            self.send_response(302)                                 # comme GitHub : vers le stockage
            self.send_header("Location", "/blob/" + p.rsplit("/", 1)[1])
            self.end_headers()
        elif p.startswith("/blob/"):
            assert self.headers.get("Range") == "bytes=0-0"          # la taille, sans tout télécharger
            self.send_response(206)
            self.send_header("Content-Range", f"bytes 0-0/{SIZE}")
            self.send_header("Content-Length", "1")
            self.end_headers()
            self.wfile.write(b"x")
        else:
            self.send_response(404)
            self.end_headers()


class Secours(unittest.TestCase):
    def setUp(self):
        Faux.api_code, Faux.asset_ok = 403, True
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Faux)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.srv.server_port}"
        env = {k: v for k, v in os.environ.items() if k != "HFIMAGE_UPDATE_URL"}
        self.patches = [mock.patch.dict(os.environ, env, clear=True),
                        mock.patch.object(updater, "LATEST_URL", base + "/api/latest"),
                        mock.patch.object(updater, "PAGE_URL", base + "/releases/latest"),
                        mock.patch.object(updater, "DOWNLOAD_BASE", base + "/download/")]
        for p in self.patches:
            p.start()
        self.base = base

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.srv.shutdown()
        self.srv.server_close()

    def test_api_limitee_page_de_secours(self):
        info = updater.check(timeout=5)
        self.assertEqual(info["version"], "9.87")
        self.assertEqual(info["url"], f"{self.base}/download/v9.87/{updater.ASSET_NAME}")
        self.assertEqual(info["size"], SIZE)
        self.assertIsNone(info["sha256"])
        self.assertTrue(updater.newer(info["version"], "1.41"))

    def test_fichier_pas_encore_publie(self):
        Faux.asset_ok = False
        info = updater.check(timeout=5)
        self.assertEqual(info["version"], "9.87")
        self.assertIsNone(info["url"])

    def test_tout_echoue_message_clair(self):
        with mock.patch.object(updater, "PAGE_URL", self.base + "/nulle-part"):
            with self.assertRaises(RuntimeError) as c:
                updater.check(timeout=5)
        self.assertEqual(str(c.exception), updater.RATE_LIMIT_MSG)
        try:
            i18n.set_lang("en")
            self.assertIn("try again in an hour", i18n.tr(str(c.exception)))
        finally:
            i18n.set_lang("fr")



class Adresse(unittest.TestCase):
    def test_adresse_officielle(self):
        # en vrai, le fichier trouvé par la page est à une adresse que download() accepte
        self.assertTrue(updater.ALLOWED[0].startswith("https://github.com/f4gopdenis-cyber/HFImage_F4GOP/"))
        self.assertEqual(updater.DOWNLOAD_BASE, updater.ALLOWED[0])


if __name__ == "__main__":
    unittest.main()
