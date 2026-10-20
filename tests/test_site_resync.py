"""1.19 : « Envoyer la page maintenant » remet aussi en ligne les dernières images (Digi-Sites)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import websync  # noqa: E402
from PIL import Image  # noqa: E402


class Ftp:
    def __init__(self):
        self.files = {}

    def cwd(self, d):
        pass

    def storbinary(self, cmd, f, *a, **k):
        self.files[cmd.split(" ", 1)[1]] = f.read()

    def quit(self):
        pass


class Resync(unittest.TestCase):
    def test_images_et_page(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i in range(4):
                p = os.path.join(d, f"{i}.png")
                Image.new("RGB", (80, 60), (i * 60, 0, 0)).save(p)
                paths.append(p)
            ftp = Ftp()
            logs = []
            w = websync.WebSync(os.path.join(d, "state.json"), log=logs.append)
            with mock.patch.object(websync.hybrid, "_ftp_connect", lambda cfg: ftp):
                w._do("sync", {"count": 2, "call": "F4GOP"}, None,
                      ([(paths[0], "F4FCE 20:50"), (os.path.join(d, "absent.png"), "X"), (paths[1], "M0JGM"),
                        (paths[2], "F1SZC")], [(paths[3], "émise par F4GOP")]), None)
            self.assertEqual(sorted(ftp.files), ["TX1.jpg", "hfimage.html", "image1.jpg", "image2.jpg", "list.txt"])
            self.assertEqual([e["caption"] for e in w.state["rx"]], ["F4FCE 20:50", "M0JGM"])
            self.assertIn(b"F4FCE 20:50", ftp.files["list.txt"])
            self.assertIn("1 émise", logs[-1])

    def test_choix_dans_la_galerie(self):
        try:
            import app
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        import types
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "a.png")
            Image.new("RGB", (8, 8)).save(f)
            items = [{"dir": "rx", "call": "F4FCE", "mode": "DATAC13-HYB", "file": f, "t": 0},
                     {"dir": "rx", "call": "F4GOP.HF", "mode": "DATAC13", "file": f, "t": 0},
                     {"dir": "rx", "call": "M0JGM", "mode": "DATAC3 aperçu", "file": f, "t": 0},
                     {"dir": "rx", "call": "F1SZC", "mode": "DATAC3", "file": os.path.join(d, "x.png"), "t": 0},
                     {"dir": "tx", "call": "F4GOP", "mode": "DATAC13-HYB", "file": f, "t": 0}]
            s = types.SimpleNamespace(gal_store=types.SimpleNamespace(items=items),
                                      conf={"web_block": "F4GOP.HF", "web_tx": True})
            s._gallery_src = app.App._gallery_src.__get__(s)
            rx, tx = app.App._web_recent(s)
        self.assertEqual([c.split()[0] for _, c in rx], ["F4FCE"])
        self.assertEqual(len(tx), 1)


if __name__ == "__main__":
    unittest.main()
