"""1.25 (demande de RK1AT) : en hybride, un fichier part tel quel, sous son nom d'origine."""
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import hybrid  # noqa: E402
import protocol  # noqa: E402


class Noms(unittest.TestCase):
    def test_nom_sur_le_serveur(self):
        n = hybrid.remote_name("RK1AT", "file", "TEST.MP4")
        self.assertRegex(n, r"^RK1AT_\d{8}_\d{6}_TEST\.MP4$")
        n = hybrid.remote_name("RK1AT", "file", "été à Paris (1).mp3")
        self.assertRegex(n, r"^RK1AT_\d{8}_\d{6}_ete_a_Paris__1_\.mp3$")
        self.assertNotIn(" ", n)
        self.assertRegex(hybrid.remote_name("F4GOP", "jpg"), r"^F4GOP_\d{8}_\d{6}\.jpg$")

    def test_menage_reconnait_les_fichiers(self):
        pat = re.compile(hybrid.mine_pattern("RK1AT"))
        for n in ("RK1AT_20261021_133402_TEST.MP4", "RK1AT_20261021_133402.jpg",
                  "RK1AT_20261021_133402_page.html"):
            self.assertTrue(pat.fullmatch(n), n)
        for n in ("index.html", "RK1ATX_20261021_133402_TEST.MP4", "RK1AT_20261021_133402.file/x"):
            self.assertFalse(pat.fullmatch(n), n)

    def test_nom_repris_du_lien(self):
        self.assertEqual(hybrid.name_from_url("http://www.rk1at.ru/hfimage/RK1AT_20261021_133402_TEST.mp4"),
                         "TEST.mp4")
        self.assertEqual(hybrid.name_from_url("http://x/y/autre%20nom.pdf"), "autre nom.pdf")


class Reception(unittest.TestCase):
    def test_fichier_brut_enregistre_sous_son_nom(self):
        try:
            import engine
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        with tempfile.TemporaryDirectory() as d:
            got = []
            eng = engine.RxEngine.__new__(engine.RxEngine)
            eng.outdir, eng.saved = d, {}
            eng.on_image = lambda info, path, png, mode: got.append((info, path))
            raw = b"\x00\x00\x00\x18ftypmp42" + os.urandom(500)
            hyb = {"id": 7, "call": "RK1AT", "crc": 0, "fmt": "file",
                   "url": "http://www.rk1at.ru/hfimage/RK1AT_20261021_133402_TEST.mp4"}
            eng.save_hybrid(hyb, raw, "DATAC13")
            info, path = got[0]
            self.assertTrue(path.endswith("TEST.mp4"), path)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), raw)
            # ancien envoi (fichier emballé) : toujours compris
            got.clear()
            eng.save_hybrid(dict(hyb, id=8, url="http://x/RK1AT_20261021_133402.file"),
                            protocol.pack_file("notes.txt", b"bonjour"), "DATAC3")
            self.assertTrue(got[0][1].endswith("notes.txt"))


if __name__ == "__main__":
    unittest.main()
