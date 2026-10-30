"""1.93 (idée de BH2RMX) : sauvegarde / restauration dans un seul .zip, chemins adaptés au nouveau PC."""
import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import backup  # noqa: E402


def w(p, data=b"x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


class Sauvegarde(unittest.TestCase):
    def setUp(self):
        self.old = tempfile.mkdtemp()                    # « ancien PC »
        self.new = tempfile.mkdtemp()                    # « nouveau PC », autre nom d'utilisateur
        self.out = os.path.join(self.old, "Documents", "HFImage")
        conf = {"callsign": "F4GOP", "folder": self.out, "rig_presets": {"IC-7300": {"radio": {"port": "COM3"}}}}
        w(os.path.join(self.old, ".hfimage.json"), json.dumps(conf))
        w(os.path.join(self.old, ".hfimage_20m.json"), json.dumps({"folder": os.path.join(self.out, "20m")}))
        w(os.path.join(self.old, "autre.json"), "{}")                      # pas à nous : jamais pris
        w(os.path.join(self.out, "wav", "begin.wav"))
        w(os.path.join(self.out, "locators.json"), "{}")
        w(os.path.join(self.out, "2026-10-30", "a.avif"), b"img")
        w(os.path.join(self.out, "fichiers", "log.adi"), b"adif")
        w(os.path.join(self.out, "galerie.json"), json.dumps([{"path": os.path.join(self.out, "2026-10-30", "a.avif")}]))
        w(os.path.join(self.out, "envoyees", "2026-10-30", "b.jpg"), b"sent")
        w(os.path.join(self.out, "journal.txt"), b"log")
        self.zip = os.path.join(tempfile.mkdtemp(), "s.zip")

    def test_parties(self):
        names = [a for _, a in backup.collect(["settings"], self.old, self.out, self.out)]
        self.assertIn("home/.hfimage.json", names)
        self.assertIn("home/.hfimage_20m.json", names)
        self.assertIn("out/wav/begin.wav", names)
        self.assertNotIn("home/autre.json", names)
        rx = [a for _, a in backup.collect(["rx"], self.old, self.out, self.out)]
        self.assertIn("rx/2026-10-30/a.avif", rx)
        self.assertIn("rx/fichiers/log.adi", rx)
        self.assertFalse(any(a.startswith(("rx/envoyees", "rx/wav")) or a == "rx/journal.txt" for a in rx))
        tx = [a for _, a in backup.collect(["tx"], self.old, self.out, self.out)]
        self.assertEqual(tx, ["tx/2026-10-30/b.jpg"])

    def test_aller_retour_autre_pc(self):
        n, _ = backup.make(self.zip, list(backup.PARTS), self.old, self.out, self.out, "1.93")
        self.assertGreater(n, 6)
        new_out = os.path.join(self.new, "Documents", "HFImage")
        info = backup.restore(self.zip, self.new, new_out, new_out)
        self.assertEqual(info["folder"], new_out)
        conf = json.load(open(os.path.join(self.new, ".hfimage.json")))
        self.assertEqual(conf["folder"], new_out)                          # chemin adapté
        self.assertEqual(conf["rig_presets"]["IC-7300"]["radio"]["port"], "COM3")
        self.assertTrue(os.path.isfile(os.path.join(new_out, "2026-10-30", "a.avif")))
        self.assertTrue(os.path.isfile(os.path.join(new_out, "envoyees", "2026-10-30", "b.jpg")))
        self.assertTrue(os.path.isfile(os.path.join(new_out, "wav", "begin.wav")))
        gal = json.load(open(os.path.join(new_out, "galerie.json")))
        self.assertEqual(gal[0]["path"], os.path.join(new_out, "2026-10-30", "a.avif"))

    def test_seulement_les_reglages(self):
        backup.make(self.zip, ["settings"], self.old, self.out, self.out)
        new_out = os.path.join(self.new, "Documents", "HFImage")
        backup.restore(self.zip, self.new, new_out, new_out)
        self.assertTrue(os.path.isfile(os.path.join(self.new, ".hfimage.json")))
        self.assertFalse(os.path.exists(os.path.join(new_out, "2026-10-30")))

    def test_zip_piege(self):
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr(backup.MANIFEST, json.dumps({"app": "HFImage", "parts": ["settings", "rx"], "home": "/x"}))
            z.writestr("rx/../../evil.txt", "x")
            z.writestr("home/.bashrc", "x")
            z.writestr("rx/ok.txt", "x")
        info = backup.restore(self.zip, self.new, self.new, os.path.join(self.new, "img"))
        self.assertEqual(info["files"], 1)
        self.assertFalse(os.path.exists(os.path.join(self.new, ".bashrc")))

    def test_pas_une_sauvegarde(self):
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("x.txt", "x")
        with self.assertRaises(ValueError):
            backup.read_manifest(self.zip)


if __name__ == "__main__":
    unittest.main()
