"""1.92 (BH2RMX) : texte waterfall retourné en LSB ; menu « CAT » de commandes personnalisées."""
import os
import sys
import types
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import app  # noqa: E402
import radio  # noqa: E402
import wavtext  # noqa: E402


class Miroir(unittest.TestCase):
    def test_choix(self):
        f = app.wft_mirror
        self.assertTrue(f("auto", "LSB-DATA1", 7058000))
        self.assertTrue(f("auto", "PKTLSB", None))
        self.assertFalse(f("auto", "USB", 7058000))           # le mode lu prime sur la bande
        self.assertTrue(f("auto", None, 7058000))             # sans CAT : sous 10 MHz = LSB
        self.assertFalse(f("auto", None, 14233000))
        self.assertFalse(f("auto", None, None))
        self.assertTrue(f("lsb", "USB", 14233000))
        self.assertFalse(f("normal", "LSB", 7058000))

    def test_spectre_retourne(self):
        bm = np.zeros((4, 40), dtype=bool)
        bm[:, :3] = True                                       # trait à gauche (fréquences basses)

        def centre(a):
            x = a.astype(float)
            sp = np.abs(np.fft.rfft(x))
            fr = np.fft.rfftfreq(len(x), 1 / 8000)
            m = (fr > 200) & (fr < 3500)
            return float((sp[m] * fr[m]).sum() / sp[m].sum())
        normal, inverse = centre(wavtext.synth(bm)), centre(wavtext.synth(bm, mirror=True))
        self.assertLess(normal, inverse - 500)


class MenuCat(unittest.TestCase):
    def test_kenwood_et_perso(self):
        sent = []
        r = radio.KenwoodRig.__new__(radio.KenwoodRig)
        r.lock = __import__("threading").Lock()
        r.ser = types.SimpleNamespace(write=sent.append, flush=lambda: None)
        r.send_raw(radio.parse_cmds("AN2;|PA1;"), delay=0)
        self.assertEqual(sent, [b"AN2;", b"PA1;"])

    def test_rigctl_icom_et_texte(self):
        r = radio.RigctlRig.__new__(radio.RigctlRig)
        got = []

        def cmd(c, n=1):
            got.append(c)
            if c.endswith(" 1"):
                raise RuntimeError("le poste ne répond pas à la commande Hamlib")   # texte : normal
            return ["send_cmd_rx: …", "Reply: \\0xFE\\0xFE\\0xE0\\0x94\\0xFB\\0xFD 6", "RPRT 0"]
        r.cmd = cmd
        r.send_raw(radio.parse_cmds("FEFE94E0160201FD|AN2;"), delay=0)
        self.assertEqual(got[0], "+W \\0xFE\\0xFE\\0x94\\0xE0\\0x16\\0x02\\0x01\\0xFD 6")
        self.assertEqual(got[1], "+W \\0x41\\0x4E\\0x32\\0x3B 1")

    def test_sans_cat(self):
        with self.assertRaises(RuntimeError):
            radio.RigBase().send_raw([b"X"])

    def test_menu(self):
        s = types.SimpleNamespace(conf={"cat_cmds": [["Antenne 2", "AN2;"], ["", "x"], "abîmé"]})
        s._cat_cmds = app.App._cat_cmds.__get__(s)
        self.assertEqual(s._cat_cmds(), [("Antenne 2", "AN2;")])


if __name__ == "__main__":
    unittest.main()
