"""Version 0.98 : éclair par défaut, fausse accroche ignorée, assistant de démarrage."""
import json
import os
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


class EclairParDefaut(unittest.TestCase):
    def conf(self, saved):
        app = _app()
        p = os.path.join(tempfile.mkdtemp(), "c.json")
        if saved is not None:
            with open(p, "w") as f:
                json.dump(saved, f)
        with mock.patch.object(app, "CONF_PATH", p):
            return app.load_conf()

    def test_nouvelle_installation(self):
        self.assertTrue(self.conf(None)["hyb_flash"])
        self.assertEqual(self.conf(None)["callsign"], "")

    def test_mise_a_jour_une_seule_fois(self):
        c = self.conf({"conf_v": 62, "hyb_flash": False, "callsign": "F4EEH"})
        self.assertTrue(c["hyb_flash"])
        self.assertEqual(c["conf_v"], 63)
        # décoché ensuite par l'utilisateur : son choix est gardé
        self.assertFalse(self.conf({"conf_v": 63, "hyb_flash": False})["hyb_flash"])


class FausseAccroche(unittest.TestCase):
    def busy(self, sync_age, last_ok_age=99):
        app = _app()
        s = types.SimpleNamespace(WAIT_HOLD_S=app.App.WAIT_HOLD_S, WAIT_SYNC_S=app.App.WAIT_SYNC_S,
                                  rig_freq=None, online={}, rx_stream=object(),
                                  v_call=types.SimpleNamespace(get=lambda: "F4GOP"))
        now = time.time()
        m = types.SimpleNamespace(sync=1 if sync_age is not None else 0,
                                  sync_since=now - (sync_age or 0), last_ok=now - last_ok_age)
        s.rx_engine = types.SimpleNamespace(modems={"DATAC0": m}, drm=None, drm_t=0)
        return app.App._freq_busy(s)

    def test_breve_accroche_ignoree(self):
        self.assertIsNone(self.busy(0.3))

    def test_vraie_accroche(self):
        self.assertEqual(self.busy(1.0), "signal DATAC0")

    def test_trame_decodee(self):
        self.assertEqual(self.busy(None, last_ok_age=1), "signal DATAC0")


class Assistant(unittest.TestCase):
    def test_trois_etapes(self):
        app = _app()
        import i18n
        home = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"HOME": home, "APPDATA": home, "LOCALAPPDATA": home}), \
                mock.patch.object(app, "CONF_PATH", os.path.join(home, "absent", "c.json")), \
                mock.patch.object(i18n, "detect_lang", lambda: "fr"), \
                mock.patch.object(app.App, "_licence_first_run", lambda self: None), \
                mock.patch.object(app.App, "net_start", lambda self: None), \
                mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: None):
            i18n.set_lang("fr")
            try:
                a = app.App()
            except Exception as e:
                self.skipTest(f"fenêtre principale impossible ici : {e}")
            try:
                self.assertTrue(a.first_run)
                a._startup_dialogs()
                w = a._wiz
                self.assertTrue(w.winfo_exists())
                warned = []
                with mock.patch("setupwiz.messagebox.showwarning", lambda *x, **k: warned.append(x)):
                    a.v_call.set("")
                    w.next()                                   # indicatif vide : refusé
                    self.assertEqual((w.step, len(warned)), (0, 1))
                    a.v_call.set("f4gop")
                    a.v_loc.set("in98qr")
                    w.next()
                    w.next()
                    self.assertEqual(w.step, 2)
                    with mock.patch.object(a, "_in_changed", lambda: a.save_conf(quiet=True)):
                        w.next()                               # Terminer
                self.assertFalse(w.winfo_exists())
                self.assertEqual((a.conf["callsign"], a.conf["locator"]), ("F4GOP", "IN98QR"))
            finally:
                a.destroy()


if __name__ == "__main__":
    unittest.main()
