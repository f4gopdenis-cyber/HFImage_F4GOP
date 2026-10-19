"""Version 0.99 : indicatifs d'écouteurs (SWL)."""
import os
import sys
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


class Swl(unittest.TestCase):
    def test_reconnus(self):
        app = _app()
        for c in ("PA0041SWL", "F-12345", "14VD274", "14FR79", "ONL1234", "de-ab123"):
            self.assertTrue(app.is_swl(c), c)
        for c in ("F4GOP", "F4GOP/P", "2E0ABC", "4X1AB", "9A1A", "M0JGM", "G7VQV", "DL1ABC", "EA8/F4GOP",
                  "F11GYT", "AA3SO", ""):
            self.assertFalse(app.is_swl(c), c)

    def test_assistant_accepte(self):
        try:
            import setupwiz
        except ImportError as e:
            self.skipTest(str(e))
        for c in ("F4GOP", "F4GOP/P", "PA0041SWL", "F-12345", "14VD274", "EA8/F4GOP"):
            self.assertTrue(setupwiz.CALL_RE.match(c), c)
        for c in ("", "AB", "SWL", "F4GOP!"):
            self.assertFalse(setupwiz.CALL_RE.match(c), c)

    def test_swl_n_emet_jamais(self):
        app = _app()
        logs, shown = [], []
        s = types.SimpleNamespace(tx_busy=False, v_call=types.SimpleNamespace(get=lambda: "PA0041SWL"),
                                  log=logs.append)
        with mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: shown.append(a[1])):
            self.assertFalse(app.App._start_job(s, {"kind": "ack"}, quiet=True))
            self.assertFalse(app.App._start_job(s, {"kind": "image"}))
        self.assertEqual(len(logs), 1)
        self.assertIn("Internet", shown[0])

    def test_indicatif_complet(self):
        app = _app()
        s = types.SimpleNamespace(online={"x": {"call": "PA0041SWL"}, "y": {"call": "F4EEH"}}, heard={})
        self.assertEqual(app.App._full_call(s, "PA0041SW"), "PA0041SWL")
        self.assertEqual(app.App._full_call(s, "F4EEH"), "F4EEH")
        s.online["z"] = {"call": "PA0041SWX"}            # ambigu : on ne devine pas
        self.assertEqual(app.App._full_call(s, "PA0041SW"), "PA0041SW")


if __name__ == "__main__":
    unittest.main()
