"""Tests de sécurité de la réception (version 0.69).

Lancer depuis la racine du dépôt :  python -m unittest discover -s tests -v

- un indicatif reçu par radio ne peut pas faire écrire un fichier hors du dossier de réception ;
- les téléchargements hybrides annoncés par radio refusent les serveurs locaux / privés ;
- l'hybride EasyPal refuse un fichier de plus de 8 Mo.
"""
import ftplib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import easypal_hybrid  # noqa: E402
import engine  # noqa: E402
import hybrid  # noqa: E402
import protocol  # noqa: E402

PIEGES = ["\\..\\..\\..\\x", "../../../x", "C:x", "..", "a\\b", "F4GOP:evil", "\\\\srv\\share", "x\0y"]


def files_in(root):
    out = []
    for d, _, names in os.walk(root):
        out += [os.path.join(d, n) for n in names]
    return out


class SafeCall(unittest.TestCase):
    def test_indicatifs_normaux(self):
        self.assertEqual(engine.safe_call("F4GOP"), "F4GOP")
        self.assertEqual(engine.safe_call("f4gop/p"), "F4GOP-P")
        self.assertEqual(engine.safe_call("EA8/F4GOP/QRP"), "EA8-F4GOP-QRP")
        self.assertEqual(engine.call_suffix("F4GOP/P"), "_F4GOP-P")
        self.assertEqual(engine.call_suffix("?"), "")
        self.assertEqual(engine.call_suffix(""), "")

    def test_indicatifs_pieges(self):
        for c in PIEGES:
            s = engine.safe_call(c)
            for bad in ("\\", "/", ":", ".", "\0"):
                self.assertNotIn(bad, s, c)

    def test_inside(self):
        with tempfile.TemporaryDirectory() as d:
            engine.inside(d, os.path.join(d, "a", "b.jpg"))
            with self.assertRaises(ValueError):
                engine.inside(d, os.path.join(d, "..", "x.jpg"))


class SaveAvecIndicatifPiege(unittest.TestCase):
    """Bout à bout : RxEngine._save / _save_drm avec un indicatif hostile."""

    def make(self, root):
        out = os.path.join(root, "HFImage")
        os.makedirs(out)
        rx = engine.RxEngine.__new__(engine.RxEngine)
        rx.outdir, rx.saved, rx.drm_files = out, {}, 0
        rx.on_image = lambda *a, **k: None
        rx.on_drm_hybrid = lambda *a, **k: None
        return rx, out

    def check_all_inside(self, root, out):
        for p in files_in(root):
            self.assertTrue(os.path.realpath(p).startswith(os.path.realpath(out) + os.sep), p)

    def test_fichier_hfimage(self):
        for c in PIEGES:
            with tempfile.TemporaryDirectory() as root:
                rx, out = self.make(root)
                data = protocol.pack_file("evil.bat", b"echo pwned")
                rx._save(({"id": 1, "call": c, "fmt": "file"}, data), "DATAC1X")
                self.check_all_inside(root, out)

    def test_texte_hfimage(self):
        for c in PIEGES:
            with tempfile.TemporaryDirectory() as root:
                rx, out = self.make(root)
                rx._save(({"id": 2, "call": c, "fmt": "txt"}, protocol.pack_text("bonjour")), "DATAC1")
                self.check_all_inside(root, out)

    def test_fichier_easypal(self):
        for c in PIEGES:
            with tempfile.TemporaryDirectory() as root:
                rx, out = self.make(root)
                rx._save_drm({"data": b"\x00\x01binaire", "callsign": c, "name": "evil.bat",
                              "snr": 10.0, "mode": "B"})
                rx._save_drm({"data": "73 de F4GOP".encode(), "callsign": c, "name": "msg.txt",
                              "snr": 10.0, "mode": "B"})
                self.check_all_inside(root, out)


class ServeursAnnonces(unittest.TestCase):
    def test_adresses_refusees(self):
        for h in ("127.0.0.1", "192.168.1.10", "10.0.0.1", "172.16.5.5", "169.254.1.1",
                  "100.64.0.1", "0.0.0.0", "::1", "fe80::1", "::ffff:192.168.1.1", ""):
            with self.assertRaises(hybrid.Refused, msg=h):
                hybrid.public_address(h, 21)

    def test_adresse_publique(self):
        self.assertEqual(hybrid.public_address("8.8.8.8", 21), "8.8.8.8")

    def test_hybride_hfimage_lien_local(self):
        with self.assertRaises(hybrid.Refused):
            hybrid.download_retry("http://192.168.1.1/image.jpg", 1000, 0, wait=0)

    def test_hybride_easypal_serveur_local(self):
        acc = {"host": "127.0.0.1", "user": "a", "password": "b", "dir": ""}
        with self.assertRaises(hybrid.Refused):
            easypal_hybrid.download(acc, "de_F4GOP-1-x.jpg", wait=0)


class FauxFTP:
    """Serveur FTP simulé qui envoie `total` octets (et annonce ou non sa taille)."""
    total, announce = 0, True

    def __init__(self, timeout=None):
        pass

    def connect(self, host, port):
        self.host = host

    def login(self, user, pw):
        pass

    def cwd(self, path):
        pass

    def size(self, name):
        if not FauxFTP.announce:
            raise ftplib.error_perm("550 SIZE not allowed")
        return FauxFTP.total

    def retrbinary(self, cmd, cb):
        left = FauxFTP.total
        while left > 0:
            n = min(65536, left)
            cb(b"\0" * n)
            left -= n

    def quit(self):
        pass

    close = quit


class TailleEasyPal(unittest.TestCase):
    acc = {"host": "ftp.exemple.org", "user": "a", "password": "b", "dir": ""}

    def run_dl(self, total, announce):
        FauxFTP.total, FauxFTP.announce = total, announce
        with mock.patch.object(ftplib, "FTP", FauxFTP), mock.patch.object(ftplib, "FTP_TLS", FauxFTP), \
                mock.patch.object(hybrid, "public_address", lambda h, p: "93.184.216.34"):
            return easypal_hybrid.download(self.acc, "de_F4GOP-1-x.jpg", tries=1, wait=0)

    def test_petit_fichier(self):
        self.assertEqual(len(self.run_dl(50_000, True)), 50_000)

    def test_trop_gros_annonce(self):
        with self.assertRaises(hybrid.Refused):
            self.run_dl(hybrid.MAX_DOWNLOAD + 1, True)

    def test_trop_gros_sans_size(self):
        with self.assertRaises(hybrid.Refused):
            self.run_dl(hybrid.MAX_DOWNLOAD + 1, False)


if __name__ == "__main__":
    unittest.main()
