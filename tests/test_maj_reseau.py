"""2.58 (Keith Woodley) : mise à jour téléchargée dans un dossier local puis copiée à côté du programme
(programme sur un disque réseau) ; en cas d'échec, l'ancien programme est remis et le chemin donné."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import updater  # noqa: E402


class MajReseau(unittest.TestCase):
    def setUp(self):
        self.prog = tempfile.mkdtemp()                     # « disque réseau » du programme
        self.exe = os.path.join(self.prog, "HFImage_F4GOP_Linux")
        with open(self.exe, "wb") as f:
            f.write(b"ancien")
        self.new = os.path.join(tempfile.mkdtemp(), "HFImage_F4GOP_9.99_Linux")
        with open(self.new, "wb") as f:
            f.write(b"nouveau")

    def test_dossier_de_travail_local(self):
        d = updater.work_dir()
        self.assertTrue(d.startswith(tempfile.gettempdir()))
        self.assertTrue(os.path.isdir(d))

    def test_installation_par_copie(self):
        with mock.patch.object(updater, "frozen", return_value=True), \
                mock.patch.object(updater.sys, "executable", self.exe), \
                mock.patch.object(updater.subprocess, "Popen") as po:
            self.assertTrue(updater.install(self.new))
        self.assertEqual(open(self.exe, "rb").read(), b"nouveau")
        self.assertFalse(os.path.exists(self.new))
        po.assert_called_once()

    def test_echec_ancien_remis_et_chemin_donne(self):
        with mock.patch.object(updater, "frozen", return_value=True), \
                mock.patch.object(updater.sys, "executable", self.exe), \
                mock.patch.object(updater.shutil, "copyfile", side_effect=OSError(2, "No such file or directory")), \
                mock.patch.object(updater.subprocess, "Popen") as po:
            with self.assertRaises(updater.InstallError) as c:
                updater.install(self.new)
        self.assertEqual(c.exception.path, self.new)
        self.assertTrue(os.path.exists(self.new))               # la nouvelle version reste disponible
        self.assertEqual(open(self.exe, "rb").read(), b"ancien")  # l'ancien programme est remis
        po.assert_not_called()


if __name__ == "__main__":
    unittest.main()
