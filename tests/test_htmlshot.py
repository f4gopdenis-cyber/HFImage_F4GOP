"""Version 0.81 : page HTML capturée en image (Edge / Chrome headless)."""
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import htmlshot  # noqa: E402

PAGE = """<!DOCTYPE html><html><head><title>Test</title><style>
body{margin:0;background:#1060c0} p{color:yellow;font:bold 60px sans-serif;margin:40px}
</style></head><body><p>HFImage F4GOP</p><div style="width:200px;height:120px;background:red;margin:40px"></div>
</body></html>"""

FAKE = r'''#!{py}
import sys
from PIL import Image
args = sys.argv[1:]
assert "--headless" in args and any(a.startswith("--user-data-dir=") for a in args), args
assert args[-1].startswith("file:"), args
w, h = (int(v) for v in next(a for a in args if a.startswith("--window-size="))[14:].split(","))
out = next(a for a in args if a.startswith("--screenshot="))[13:]
Image.new("RGB", (w, h), (16, 96, 192)).save(out)
'''


class Capture(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.html = os.path.join(self.d, "Antenne test.html")
        with open(self.html, "w", encoding="utf-8") as f:
            f.write(PAGE)

    def test_is_html(self):
        self.assertTrue(htmlshot.is_html("C:/x/Antenne.HTML"))
        self.assertTrue(htmlshot.is_html("page.htm"))
        self.assertFalse(htmlshot.is_html("photo.jpg"))

    @unittest.skipIf(sys.platform.startswith("win"), "faux navigateur (script) : hors Windows")
    def test_faux_navigateur(self):
        fake = os.path.join(self.d, "fakebrowser")
        with open(fake, "w") as f:
            f.write(FAKE.replace("{py}", sys.executable))
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        out = htmlshot.render(self.html, os.path.join(self.d, "out.png"), (800, 600), browser=fake)
        from PIL import Image
        self.assertEqual(Image.open(out).size, (800, 600))

    def test_utf8_non_declare(self):
        d = tempfile.mkdtemp()
        cas = {"utf8.html": ("<p>Département 61</p>".encode("utf-8"), True),
               "declare.html": ('<meta charset="utf-8"><p>Département</p>'.encode("utf-8"), False),
               "cp1252.html": ("<p>Département</p>".encode("cp1252"), False),
               "ascii.html": (b"<p>Departement</p>", False)}
        for name, (raw, copie) in cas.items():
            src = os.path.join(self.d, name)
            with open(src, "wb") as f:
                f.write(raw)
            cp = htmlshot._utf8_copy(src, d)
            self.assertEqual(cp is not None, copie, name)
            if cp:
                with open(cp, "rb") as f:
                    out = f.read()
                self.assertTrue(out.startswith(b'<meta charset="utf-8"><base href="file:'), out[:80])
                self.assertTrue(out.endswith(raw))

    def test_sans_navigateur(self):
        with self.assertRaises(RuntimeError):
            htmlshot.render(self.html, os.path.join(self.d, "x.png"), browser=os.path.join(self.d, "absent.exe"))

    def test_vrai_navigateur(self):
        """Sous Windows (Edge présent sur les machines de GitHub) : vraie capture de la page."""
        exe = htmlshot.find_browser()
        if not exe:
            self.skipTest("ni Edge ni Chrome sur cette machine")
        out = htmlshot.render(self.html, os.path.join(self.d, "vraie.png"), (1024, 768), wait_ms=2000)
        from PIL import Image
        im = Image.open(out).convert("RGB")
        self.assertEqual(im.size, (1024, 768))
        self.assertEqual(im.getpixel((900, 700))[:3], (16, 96, 192))         # fond bleu de la page
        r, g, b = im.getpixel((140, 200))                                    # carré rouge
        self.assertTrue(r > 200 and g < 60 and b < 60, (r, g, b))
        dst = os.environ.get("HFIMAGE_SHOT_OUT")
        if dst:
            im.save(dst)


if __name__ == "__main__":
    unittest.main()
