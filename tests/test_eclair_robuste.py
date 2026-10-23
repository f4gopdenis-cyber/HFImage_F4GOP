"""Version 0.93 : annonce hybride éclair en DATAC13 (+ DATAC0 pour les anciennes versions)."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    import channel
    import engine
    import qrmfilter
    from modem import Modem
except OSError as e:                     # pas de libcodec2
    engine = None
    _err = str(e)


def rx(audio):
    got = []
    r = engine.RxEngine("F4GOP", tempfile.mkdtemp(), on_hybrid=lambda h, mode: got.append((h, mode)))
    x = np.concatenate([np.asarray(audio, np.float64), np.zeros(24000)])
    for i in range(0, len(x), 4000):
        r.process(np.clip(x[i:i + 4000], -32767, 32767).astype(np.int16))
    return got


@unittest.skipIf(engine is None, "libcodec2 absente")
class EclairRobuste(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(4000)                # données fixes : essai reproductible
        self.h = engine.HybridTransmission(rng.bytes(4000), "jpeg", "G7VQV", "https://x/y.jpg", flash=True)

    def test_composition(self):
        self.assertEqual([(m.mode, n) for m, n in self.h.parts], [("DATAC13", 3), ("DATAC0", 2)])
        self.assertAlmostEqual(self.h.estimate_s(), len(self.h.audio()) / 8000, places=2)
        self.assertLess(self.h.estimate_s(), 10)

    def test_une_seule_annonce(self):
        got = rx(self.h.audio())
        self.assertEqual(len(got), 1)                    # 5 copies, 2 modes : une seule annonce
        self.assertTrue(got[0][0]["flash"])
        self.assertEqual(got[0][0]["key"], self.h.key)

    def test_ancienne_version_recoit_le_datac0(self):
        m = Modem("DATAC0", 1)
        old = engine.RX_MODES
        try:
            engine.RX_MODES = tuple(x for x in old if x != "DATAC13")
            # sur l'air (bruit réel) : sans aucun bruit, le coupe-QRM voit un plancher nul et
            # peut abîmer le DATAC0 qui suit le DATAC13 (artefact de simulation, ~10 % des tirages)
            got = rx(channel.apply(self.h.audio(), 8000, 10.0, "none", 7))
        finally:
            engine.RX_MODES = old
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1], "DATAC0")
        m.close()

    def test_passe_a_moins_7_db(self):
        y = channel.apply(self.h.audio(), 8000, -7.0, "none", 3)
        got = rx(y)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1], "DATAC13")

    def test_coupe_qrm_ne_mange_pas_le_datac13(self):
        """0.93 : la référence du coupe-QRM est prise sur les porteuses du mode : à fort S/B,
        les 3 porteuses du DATAC13 ne doivent pas être prises pour du QRM."""
        m = Modem("DATAC13", 1)
        x = np.concatenate([m.modulate([b"0123456789abcd"]), np.zeros(12000, np.int16)])
        y = qrmfilter.QrmFilter("DATAC13").process(channel.apply(x, 8000, 20.0, "none", 1))
        r = Modem("DATAC13", 1)
        ok = [p for p, _ in r.demodulate(y)] + [p for p, _ in r.demodulate(np.zeros(16000, np.int16))]
        self.assertIn(b"0123456789abcd", ok)


    def test_analyseur_wav(self):
        """0.96 : l'analyseur de fichiers WAV reconnaît l'annonce éclair DATAC13."""
        import wave
        import wavanalyze
        p = os.path.join(tempfile.mkdtemp(), "eclair.wav")
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(np.concatenate([np.zeros(8000, np.int16), self.h.audio(),
                                          np.zeros(16000, np.int16)]).tobytes())
        rep = wavanalyze.analyze(p)
        ok13 = sum(1 for e in rep["modes"]["DATAC13"]["events"] if e[1])
        self.assertEqual(ok13, 3)
        self.assertTrue(any("annonce hybride éclair" in t for _, t in rep["diag"]))

    def test_waterfall_connait_datac13(self):
        import waterfall
        lo, hi, _ = waterfall.MODE_BANDS["DATAC13"]
        self.assertLess(hi - lo, 300)


if __name__ == "__main__":
    unittest.main()
