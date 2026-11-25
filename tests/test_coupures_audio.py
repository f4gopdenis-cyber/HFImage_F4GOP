"""2.53 : coupures de son en réception écrites dans le journal ; tampon d'entrée « haut »."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "app.py")


class Coupures(unittest.TestCase):
    def test_tampon_haut(self):
        s = open(SRC, encoding="utf-8").read()
        i = s.index("self.rx_stream = S.InputStream(")
        self.assertIn('latency="high"', s[i:i + 200])
        self.assertIn("status.input_overflow", s)

    def test_journal(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                logs = []
                with mock.patch.object(a, "log", side_effect=logs.append):
                    a._in_overflows = 3
                    a._audio_health_t = 0
                    a._audio_health()
                    a._audio_health_t = 0
                    a._audio_health()                       # rien de nouveau : pas de 2e ligne
                self.assertEqual(len(logs), 1)
                self.assertIn("3 sound dropout", logs[0])
            finally:
                a.destroy()
                import i18n
                i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
