"""Version 0.92 : Hamlib manquant au moment d'émettre -> installation proposée."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import radio  # noqa: E402


class Offre(unittest.TestCase):
    def run_tx(self, ptt, answer, install_ok=True, after=True):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        logs, shown = [], []

        def missing():
            raise radio.HamlibMissing()

        class Stub:
            conf = {}
            _rig_open = staticmethod(missing)
            log = staticmethod(logs.append)
            log_exc = staticmethod(lambda *a: logs.append(a))
            ui = staticmethod(lambda fn, *a: fn(*a))
            _offer_hamlib = lambda self: app.App._offer_hamlib(self)
            _hamlib_installed = lambda self, d, e: app.App._hamlib_installed(self, d, e)

        def install(progress=None):
            if not install_ok:
                raise OSError("pas d'Internet")
            return "C:/x"

        class T:
            def __init__(self, target, daemon):
                self.t = target

            def start(self):
                self.t()
        mb = app.messagebox
        with mock.patch.object(mb, "askyesno", lambda *a, **k: shown.append(("ask", a[1])) or answer), \
                mock.patch.object(mb, "showinfo", lambda *a, **k: shown.append(("info", a[1]))), \
                mock.patch.object(mb, "showerror", lambda *a, **k: shown.append(("err", a[1]))), \
                mock.patch.object(radio, "install_hamlib", install), \
                mock.patch.object(radio, "find_rigctld", lambda: "C:/x/rigctld.exe" if after else None), \
                mock.patch.object(app.threading, "Thread", T):
            ok = app.App._check_rig_before_tx(Stub(), {"rig": "hamlib:2041", "ptt": ptt, "tx_audio": "rear"})
        return ok, shown

    def test_propose_et_installe(self):
        ok, shown = self.run_tx("CAT", True)
        self.assertFalse(ok)
        self.assertEqual([k for k, _ in shown], ["ask", "info"])
        self.assertIn("relancer", shown[1][1])

    def test_refus(self):
        ok, shown = self.run_tx("CAT", False)
        self.assertFalse(ok)
        self.assertEqual([k for k, _ in shown], ["ask"])

    def test_echec_internet(self):
        ok, shown = self.run_tx("CAT", True, install_ok=False)
        self.assertEqual(shown[-1][0], "err")
        self.assertIn("antivirus", shown[-1][1])

    def test_antivirus(self):
        ok, shown = self.run_tx("CAT", True, after=False)
        self.assertIn("quarantaine", shown[-1][1])

    def test_ptt_rts_emet_quand_meme(self):
        ok, shown = self.run_tx("RTS", True)
        self.assertTrue(ok)
        self.assertEqual(shown, [])


if __name__ == "__main__":
    unittest.main()
