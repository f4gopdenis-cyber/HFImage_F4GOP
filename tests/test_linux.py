"""1.23 : version Linux (menu des applications, mise à jour, polices, Hamlib, ports série)."""
import io
import os
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


@unittest.skipIf(sys.platform.startswith("win"), "Linux seulement")
class Linux(unittest.TestCase):
    def test_entree_menu(self):
        try:
            import app
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": os.path.join(d, "share"), "HOME": d}):
                os.makedirs(os.path.join(d, "Desktop"))
                app.linux_menu_entry(["/opt/HF Image/HFImage_F4GOP_Linux", "--profil", "20m"],
                                     "HFImage 20m", "hfimage-f4gop-20m", desktop=True)
                f = os.path.join(d, "share", "applications", "hfimage-f4gop-20m.desktop")
                with open(f) as fh:
                    txt = fh.read()
                self.assertIn("Exec='/opt/HF Image/HFImage_F4GOP_Linux' --profil 20m", txt)
                self.assertIn("Categories=HamRadio", txt)
                self.assertTrue(os.path.exists(os.path.join(d, "Desktop", "hfimage-f4gop-20m.desktop")))

    def test_mise_a_jour_archive(self):
        import updater
        with tempfile.TemporaryDirectory() as d:
            arch = os.path.join(d, "HFImage_F4GOP_9.9.tar.gz")
            with tarfile.open(arch, "w:gz") as t:
                for name, data in (("../evil", b"x"), ("HFImage_F4GOP_Linux", b"\x7fELF-binaire")):
                    ti = tarfile.TarInfo(name)
                    ti.size = len(data)
                    t.addfile(ti, io.BytesIO(data))
            out = updater._extract_linux(arch)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"\x7fELF-binaire")
            self.assertTrue(os.access(out, os.X_OK))
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(d), "evil")))
        self.assertEqual(updater.ASSET_NAME, "HFImage_F4GOP_Linux.tar.gz")

    def test_polices_et_hamlib(self):
        import radio
        import trafic
        f = trafic.font("Arial", 20)                     # Arial absente : police libre équivalente
        self.assertIsNotNone(f)
        self.assertFalse(any(k.startswith("omnirig") for k in radio.rig_keys()))
        with mock.patch("shutil.which", lambda n: "/usr/bin/rigctld" if n == "rigctld" else None):
            self.assertEqual(radio.find_rigctld(), "/usr/bin/rigctld")
        with self.assertRaises(RuntimeError) as cm:
            radio.install_hamlib()
        self.assertIn("apt install", str(cm.exception))

    def test_port_serie_refuse(self):
        import audio
        import serial

        def boom(*a, **k):
            raise serial.SerialException("[Errno 13] could not open port /dev/ttyUSB0: Permission denied")
        with mock.patch.object(serial, "Serial", boom):
            with self.assertRaises(RuntimeError) as cm:
                audio.open_serial("/dev/ttyUSB0", 115200)
        self.assertIn("dialout", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
