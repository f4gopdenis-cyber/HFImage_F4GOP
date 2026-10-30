"""Version 0.78 : passage automatique en DATA en gardant la bande latérale (LSB-DATA / USB-DATA)."""
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import radio  # noqa: E402

# codes Kenwood : 1 LSB, 2 USB, C LSB-DATA1, D USB-DATA1 (cf. audio.KENWOOD_MODES)


class FakeKenwood(radio.KenwoodRig):
    """Poste Kenwood simulé : retient le mode, répond à OM0; / SF0;, comprend OM0x, MDx, DAx."""

    def __init__(self, model, mode):
        self.model, self.cfg, self.port, self.baud = model, {}, "COM9", 115200
        self.lock = threading.Lock()
        self.base, self.data = mode, False            # base : « 1 » LSB ou « 2 » USB
        self.sent = []

    def write(self, cmd):
        self.sent.append(cmd)
        if cmd.startswith("OM0"):
            c = cmd[3]
            if c in "CD":
                self.base, self.data = ("1" if c == "C" else "2"), True
            else:
                self.base, self.data = c, False
        elif cmd.startswith("MD"):
            self.base, self.data = cmd[2], False
        elif cmd.startswith("DA"):
            self.data = cmd[2] == "1"
        elif cmd.startswith("SF0") and len(cmd) == 16:     # TS-890 : mode par SF (comme Hamlib)
            c = cmd[14]
            self.base, self.data = {"1": ("1", False), "2": ("2", False), "C": ("1", True),
                                    "D": ("2", True)}[c]

    def query(self, cmd, timeout=0.6):
        code = {("1", False): "1", ("2", False): "2", ("1", True): "C", ("2", True): "D"}[(self.base, self.data)]
        if cmd == "SF0;":
            return "SF0" + "0" * 11 + code + ";"
        if cmd == "OM0;":
            return f"OM0{code};"
        return ""


class Kenwood(unittest.TestCase):
    def check(self, model, start, expect_mode, expect_cmds):
        r = FakeKenwood(model, start)
        radio.time.sleep, old = (lambda s: None), radio.time.sleep
        try:
            ok, msg = r.set_mode("data")
        finally:
            radio.time.sleep = old
        self.assertTrue(ok, msg)
        self.assertEqual(r.mode(), expect_mode)
        self.assertEqual(r.sent, expect_cmds)

    def test_ts990(self):
        self.check("TS-990S", "1", "LSB-DATA1", ["OM0C;"])
        self.check("TS-990S", "2", "USB-DATA1", ["OM0D;"])

    def test_ts890(self):
        # 1.60 : le TS-890 change de mode par SF (fréquence gardée), comme Hamlib
        self.check("TS-890S", "1", "LSB-DATA1", ["SF0" + "0" * 11 + "C;"])
        self.check("TS-890S", "2", "USB-DATA1", ["SF0" + "0" * 11 + "D;"])

    def test_ts590(self):
        self.check("TS-590SG", "1", "LSB-DATA1", ["MD1;", "DA1;"])
        self.check("TS-590SG", "2", "USB-DATA1", ["MD2;", "DA1;"])


class Bande(unittest.TestCase):
    def test_is_lsb(self):
        for m in ("LSB", "LSB-DATA1", "PKTLSB", "DIG-L", "lsb-d"):
            self.assertTrue(radio.RigBase.is_lsb(m), m)
        for m in ("USB", "USB-DATA1", "PKTUSB", "DIG-U", "", None, "CW"):
            self.assertFalse(radio.RigBase.is_lsb(m), m)

    def test_omnirig_lsb(self):
        r = radio.OmniRigRig.__new__(radio.OmniRigRig)
        r.lock, r._tid = threading.Lock(), threading.get_ident()
        state = {"mode": 0x4000000}                    # LSB
        r.rig = type("R", (), {"Mode": property(lambda s: state["mode"],
                                                lambda s, v: state.__setitem__("mode", v))})()
        radio.time.sleep, old = (lambda s: None), radio.time.sleep
        try:
            r.set_mode("data")
        finally:
            radio.time.sleep = old
        self.assertEqual(r.mode(), "DIG-L")



class AvantEmission(unittest.TestCase):
    """0.80 : contrôle du mode DATA dès que le CAT est relié, quel que soit le PTT."""

    def run_check(self, ptt, tx_audio, start="1", action="switch"):
        try:
            import app
        except ImportError as e:                         # pas de tkinter sur cette machine
            self.skipTest(str(e))
        rig = FakeKenwood("TS-890S", start)
        rig.freq = lambda: 7058000
        logs = []

        class Stub:
            conf = {"data_action": action}                # ancien réglage : converti (1.94)
            data_policy = app.App.data_policy
            _rig_open = staticmethod(lambda: rig)
            _rig_open_now = staticmethod(lambda: rig)
            log = staticmethod(logs.append)
            _rig_status = app.App._rig_status
        cfg = {"rig": "hamlib:2041", "ptt": ptt, "tx_audio": tx_audio, "set_mode": "none"}
        radio.time.sleep, old = (lambda s: None), radio.time.sleep
        try:
            ok = app.App._check_rig_before_tx(Stub(), cfg)
        finally:
            radio.time.sleep = old
        return ok, rig, logs

    def test_avant_emission_ne_touche_plus_au_mode(self):
        """1.94 : le mode DATA ne se règle plus qu'avec le bouton « DATA auto » (au moment d'émettre) ;
        le contrôle avant émission ouvre seulement la liaison CAT."""
        for ptt, start in (("RTS", "1"), ("CAT", "2")):
            ok, rig, logs = self.run_check(ptt, "rear", start=start)
            self.assertTrue(ok)
            self.assertEqual(rig.mode(), "LSB" if start == "1" else "USB")

    def test_avant_micro_inchange(self):
        ok, rig, _ = self.run_check("VOX", "front")
        self.assertTrue(ok)
        self.assertEqual(rig.mode(), "LSB")

    def test_emettre_sans_rien_dire(self):
        """Ancien « Émettre sans rien dire » = « Ne pas toucher au mode du poste » (1.94)."""
        ok, rig, logs = self.run_check("RTS", "rear", action="send")
        self.assertTrue(ok)
        self.assertEqual(rig.mode(), "LSB")


if __name__ == "__main__":
    unittest.main()
