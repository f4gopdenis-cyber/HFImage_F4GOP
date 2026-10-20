"""1.15 (demande de RK1AT) : sur notre serveur FTP, on ne garde que nos dernières images hybrides."""
import ftplib
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import easypal_hybrid  # noqa: E402
import hybrid  # noqa: E402


class FakeFtp:
    def __init__(self, names, full_paths=False):
        self.files = list(names)
        self.full = full_paths

    def nlst(self):
        return [("/www/hfimage/" + n) if self.full else n for n in self.files]

    def delete(self, n):
        if n not in self.files:
            raise ftplib.error_perm("550 not found")
        self.files.remove(n)


class Menage(unittest.TestCase):
    def test_hfimage_garde_les_dernieres(self):
        names = [f"F4GOP_20261020_1{i}0000.jpg" for i in range(5)] + [
            "index.html", "photo.jpg", "F4GOPX_20261020_100000.jpg", "F4EEH_20261020_100000.avif",
            "F4GOP_20261020_190000.webp"]
        ftp = FakeFtp(names, full_paths=True)
        logs = []
        gone = hybrid.prune(ftp, hybrid.mine_pattern("F4GOP"), 3, log=logs.append)
        self.assertEqual(sorted(gone), ["F4GOP_20261020_100000.jpg", "F4GOP_20261020_110000.jpg",
                                        "F4GOP_20261020_120000.jpg"])
        for keep in ("index.html", "photo.jpg", "F4GOPX_20261020_100000.jpg", "F4EEH_20261020_100000.avif",
                     "F4GOP_20261020_190000.webp", "F4GOP_20261020_140000.jpg", "F4GOP_20261020_130000.jpg"):
            self.assertIn(keep, ftp.files)
        self.assertTrue(logs)

    def test_derniere_seulement_et_toutes(self):
        names = [f"RK1AT_20261020_10000{i}.jpg" for i in range(4)]
        ftp = FakeFtp(names)
        self.assertEqual(hybrid.prune(ftp, hybrid.mine_pattern("RK1AT"), 0), [])     # toutes
        self.assertEqual(len(ftp.files), 4)
        hybrid.prune(ftp, hybrid.mine_pattern("RK1AT"), 1)
        self.assertEqual(ftp.files, ["RK1AT_20261020_100003.jpg"])

    def test_easypal_par_numero(self):
        call = "F4GOP/P"
        names = [easypal_hybrid.file_name(call, n, "ma-photo", "jpg") for n in (9, 10, 2, 11)] + [
            easypal_hybrid.file_name("F4EEH", 1, "x", "jpg"), "de_F4GOP-1-x.jpg"]
        ftp = FakeFtp(names)
        hybrid.prune(ftp, easypal_hybrid.mine_pattern(call), 2, order=easypal_hybrid._order_for(call))
        mine = sorted(n for n in ftp.files if n.startswith("de_F4GOP-P-"))
        self.assertEqual(mine, ["de_F4GOP-P-10-ma-photo.jpg", "de_F4GOP-P-11-ma-photo.jpg"])
        self.assertIn("de_F4EEH-1-x.jpg", ftp.files)
        self.assertIn("de_F4GOP-1-x.jpg", ftp.files)          # autre indicatif (sans /P) : pas touché

    def test_liste_impossible(self):
        class Bad(FakeFtp):
            def nlst(self):
                raise ftplib.error_perm("550 No files found")
        self.assertEqual(hybrid.prune(Bad([]), hybrid.mine_pattern("F4GOP"), 1), [])


if __name__ == "__main__":
    unittest.main()
