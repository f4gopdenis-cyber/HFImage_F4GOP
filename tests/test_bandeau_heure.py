"""2.50 (Keith Woodley) : heure du bandeau « Mes conditions de trafic » en UTC, en heure locale avec son
décalage, ou date seule ; remise à jour juste avant d'émettre."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import trafic  # noqa: E402


class Heure(unittest.TestCase):
    T = 1763800500          # 2025-11-22 08:35:00 UTC

    def test_utc(self):
        self.assertEqual(trafic.date_text("%Y-%m-%d", "utc", self.T), "2025-11-22 08:35 UTC")

    def test_locale_avec_decalage(self):
        if not hasattr(time, "tzset"):
            raise unittest.SkipTest("time.tzset absent (Windows)")
        with mock.patch.dict(os.environ, {"TZ": "Australia/Perth"}):
            time.tzset()
            try:
                self.assertEqual(trafic.utc_offset(self.T), "UTC+8")
                self.assertEqual(trafic.date_text("%d/%m/%Y", "local", self.T), "22/11/2025 16:35 UTC+8")
            finally:
                os.environ.pop("TZ", None)
        time.tzset()

    def test_demi_heure_et_negatif(self):
        if not hasattr(time, "tzset"):
            raise unittest.SkipTest("time.tzset absent (Windows)")
        for tz, want in (("Asia/Kolkata", "UTC+5:30"), ("America/Sao_Paulo", "UTC-3"), ("UTC", "UTC")):
            with mock.patch.dict(os.environ, {"TZ": tz}):
                time.tzset()
                try:
                    self.assertEqual(trafic.utc_offset(self.T), want)
                finally:
                    os.environ.pop("TZ", None)
            time.tzset()

    def test_date_seule(self):
        out = trafic.parts({"tc_call": False, "tc_loc": False, "tc_date": True, "tc_time": "date"})
        self.assertEqual(len(out), 1)
        self.assertNotIn(":", out[0])


class AvantEmission(unittest.TestCase):
    def test_image_refaite_si_heure_ancienne(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6WK", "licence_ok": "1.0", "lang": "en", "net_on": False,
                       "tc_on": True, "tc_date": True, "tc_time": "utc"}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                tx = mock.Mock()
                a.tx = tx
                a._tc_stamp = time.time() - 600                     # préparée il y a 10 min
                self.assertTrue(a._tc_stale(tx))
                with mock.patch.object(a, "prepare") as prep, mock.patch.object(a, "_start_job", return_value=False):
                    a.transmit(quiet=True)
                prep.assert_called_with(sync=True)
                a._tc_stamp = time.time()
                self.assertFalse(a._tc_stale(tx))                   # récente : rien à refaire
                a.conf["tc_time"] = "date"
                a._tc_stamp = time.time() - 600
                self.assertFalse(a._tc_stale(tx))                   # date seule : rien à refaire
                a.conf["tc_time"] = "utc"
                h = app.HybridJob(b"x", "jpeg", "VK6WK")
                h.pre = ("sig", "res")
                self.assertFalse(a._tc_stale(h))                    # déposée d'avance : heure du dépôt
            finally:
                a.destroy()
                import i18n
                i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
