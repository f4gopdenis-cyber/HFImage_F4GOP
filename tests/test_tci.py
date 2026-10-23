"""1.29 (demande de F4FRC, radio-club F8KLY) : SunSDR / ExpertSDR par TCI."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radio  # noqa: E402
import tci  # noqa: E402
from fake_tci import FakeTci  # noqa: E402


class Tci(unittest.TestCase):
    def setUp(self):
        import gc
        gc.collect()          # objets Tk des essais précédents libérés dans le fil principal
        self.srv = FakeTci()
        self.cfg = dict(radio.DEFAULTS, rig="tci", host=f"127.0.0.1:{self.srv.port}", ptt="CAT")

    def tearDown(self):
        self.srv.close()

    def test_lecture_et_commandes(self):
        r = radio.make_rig(self.cfg)
        try:
            self.assertEqual(r.model, "SunSDR2PRO")
            self.assertEqual(r.freq(), 7058000)
            self.assertEqual(r.mode(), "LSB")
            self.assertFalse(r.is_data(r.mode()))
            r.ptt(True)
            time.sleep(0.2)
            r.ptt(False)
            time.sleep(0.2)
            self.assertIn("TRX:0,true", self.srv.got)
            self.assertIn("TRX:0,false", self.srv.got)
            ok, msg = r.set_mode("data")                       # LSB -> DIGL
            self.assertTrue(ok, msg)
            self.assertEqual(r.mode(), "DIGL")
            self.assertTrue(r.is_data(r.mode()) and r.is_lsb(r.mode()))
            txt = r.qsy(14233000, "USB")                        # 20 m : USB, en restant en DATA
            self.assertEqual(r.freq(), 14233000)
            self.assertEqual(r.mode(), "DIGU")
            self.assertIn("14.233", txt)
            # changement fait sur le poste : poussé par ExpertSDR, lu sans rien demander
            self.srv.push("vfo:0,0,3733000;")
            time.sleep(0.3)
            self.assertEqual(r.freq(), 3733000)
        finally:
            r.close()

    def test_ptt_par_classe_ptt(self):
        r = radio.make_rig(self.cfg)
        p = radio.Ptt(self.cfg, r)
        p.tx()
        p.rx()
        time.sleep(0.2)
        p.close()
        r.close()
        self.assertEqual([g for g in self.srv.got if g.startswith("TRX")][:2], ["TRX:0,true", "TRX:0,false"])

    def test_sans_ready_et_connexion_perdue(self):
        srv = FakeTci(send_ready=False)
        try:
            c = tci.TciClient(f"127.0.0.1:{srv.port}", timeout=1)
            self.assertEqual(c.query("vfo:0,0", "VFO:0,0;"), "7058000")
            srv.close()
            time.sleep(0.3)
        finally:
            srv.close()
        r = radio.TciRig.__new__(radio.TciRig)
        r.c, r.model = c, "TCI"
        with self.assertRaises(RuntimeError):
            for _ in range(20):
                r.ptt(True)
                time.sleep(0.05)
        c.close()

    def test_serveur_absent(self):
        with self.assertRaises(tci.TciError) as cm:
            tci.TciClient("127.0.0.1:1", timeout=1)
        self.assertIn("ExpertSDR", str(cm.exception))

    def test_liste(self):
        self.assertIn("tci", radio.rig_keys())
        self.assertEqual(radio.rig_entry("tci")["kind"], "tci")
        self.assertIn("127.0.0.1:40001", radio.describe(dict(radio.DEFAULTS, rig="tci", ptt="CAT")))


if __name__ == "__main__":
    unittest.main()
