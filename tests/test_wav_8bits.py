"""2.11 : WAV 8, 24 et 32 bits acceptés comme EasyPal (avant : 16 bits seulement)."""
import os
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import engine  # noqa: E402

FS = 8000


def tone():
    t = np.arange(FS) / FS
    return (0.5 * np.sin(2 * np.pi * 1000 * t))            # -0.5 .. 0.5


def write(path, sw, ch=1):
    x = tone()
    if sw == 1:
        raw = np.round(x * 127 + 128).astype(np.uint8)
    elif sw == 2:
        raw = np.round(x * 32767).astype("<i2")
    elif sw == 3:
        v = np.round(x * 8388607).astype("<i4")
        raw = np.frombuffer(v.tobytes(), dtype=np.uint8).reshape(-1, 4)[:, :3].copy()
    else:
        raw = np.round(x * 2147483647).astype("<i4")
    if ch == 2:
        raw = np.repeat(raw.reshape(len(x), -1), 2, axis=0).reshape(-1) if sw == 3 else np.repeat(raw, 2)
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(FS)
        w.writeframes(np.ascontiguousarray(raw).tobytes())


class Wav(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def check(self, sw, ch=1):
        p = os.path.join(self.d, f"t{sw}{ch}.wav")
        write(p, sw, ch)
        x, fs = engine.read_wav_int16(p)
        self.assertEqual(fs, FS)
        self.assertEqual(x.dtype, np.int16)
        self.assertEqual(len(x), FS)
        ref = np.round(tone() * 32767)
        self.assertLess(np.max(np.abs(x.astype(float) - ref)), 400 if sw == 1 else 4)
        self.assertEqual(len(engine.read_wav_8k(p)), FS)

    def test_8_bits(self):
        self.check(1)

    def test_8_bits_stereo(self):
        self.check(1, 2)

    def test_16_bits_inchange(self):
        self.check(2)

    def test_24_bits(self):
        self.check(3)

    def test_32_bits(self):
        self.check(4)

    def test_niveau_wav_8_bits(self):
        import wavanalyze
        p = os.path.join(self.d, "n.wav")
        write(p, 1)
        wavanalyze._level(p)                                 # ne refuse plus le fichier
