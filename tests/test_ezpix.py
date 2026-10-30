"""1.84 : compatibilité EZ Pix (W3WVG) : signal GMSK fixe, liste EZPixOnAir, image « EZPix/image1 »."""
import os
import sys
import types
import unittest
import wave
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import ezpix  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def run(x, chunk=1024):
    d = ezpix.Detector()
    hits = []
    for i in range(0, len(x), chunk):
        r = d.feed(x[i:i + chunk])
        if r is not None:
            hits.append(i / 8000)
    return hits


class Signal(unittest.TestCase):
    def test_vrai_signal_ez_pix(self):
        """Émission EZ Pix 2.56 réelle (F4GOP, enregistrée le 29/10/2026) : une seule détection."""
        w = wave.open(os.path.join(HERE, "data", "ezpix_f4gop.wav"))
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        self.assertEqual(len(run(x)), 1)

    def test_notre_signal_et_bruit(self):
        rng = np.random.default_rng(3)
        m = ezpix.modulate()
        self.assertAlmostEqual(len(m) / 8000, 5.4, delta=0.2)
        sig = np.concatenate([np.zeros(8000), m, np.zeros(8000)])
        noisy = sig + rng.normal(0, np.sqrt(np.mean(m ** 2)), len(sig))        # ~0 dB
        self.assertEqual(len(run(noisy)), 1)
        self.assertEqual(run(rng.normal(0, 0.1, 8000 * 15)), [])                # bruit seul : rien

    def test_pas_de_fausse_alerte_datac(self):
        try:
            import engine
            rng = np.random.default_rng(4)
            tx = engine.Transmission(bytes(rng.integers(0, 256, 3000, dtype=np.uint8)), "avif", "F4GOP",
                                     "DATAC3", 0.25)
        except Exception as e:
            self.skipTest(str(e))
        a = np.concatenate(list(tx.audio_chunks()))
        self.assertEqual(run(a), [])


class Liste(unittest.TestCase):
    def test_noms(self):
        st = ezpix.parse_onair_name("F1JMJ_3--1733_Joel_http--3--4--4www--1qsl--1net--4f1jmj_.txt")
        self.assertEqual(st, {"call": "F1JMJ", "freq": "3.733", "name": "Joel", "url": "http://www.qsl.net/f1jmj/"})
        st = ezpix.parse_onair_name("F4GOP_7--2058_Denis_https--3--4--4www--1qsl--1net--4f0gop--4_.txt")
        self.assertEqual((st["freq"], st["url"]), ("7,058", "https://www.qsl.net/f0gop/"))
        self.assertEqual(ezpix.image_url(st), "https://www.qsl.net/f0gop/EZPix/image1")
        st = ezpix.parse_onair_name("WO8G_14-233_Keith_www!buffalo10meter!net_.txt")
        self.assertEqual(st["url"], "http://www.buffalo10meter.net/")
        st = ezpix.parse_onair_name("KT4JW_3--1803_Tim--5Winfield--5AL_http--3--4--4www--1qsl--1net--4kr4zo_.txt")
        self.assertEqual(st["name"], "Tim Winfield AL")
        self.assertIsNone(ezpix.parse_onair_name("readme.html"))

    def test_page(self):
        page = ('<a href="?C=N;O=D">Name</a><a href="/w/w3wvg/">Parent</a>'
                '<a href="F1JMJ_3--1733_Joel_http--3--4--4www--1qsl--1net--4f1jmj_.txt">x</a>'
                '<a href="DL5SN_7--2058_Sergej_http--3--4--4www--1qsl--1net--4dl5sn_.txt">x</a>'
                '<a href="DL5SN_14233_Sergej_http--3--4--4www--1qsl--1net--4dl5sn_.txt">x</a>')
        calls = sorted(s["call"] for s in ezpix.parse_onair_listing(page))
        self.assertEqual(calls, ["DL5SN", "F1JMJ"])

    def test_plusieurs_sites_meme_indicatif(self):
        """F4GOP a deux comptes qsl.net (f0gop et f4gop) : les deux sites sont regardés."""
        page = ('<a href="F4GOP_7--2058_Denis_https--3--4--4www--1qsl--1net--4f0gop--4_.txt">x</a>'
                '<a href="F4GOP_7--2058_Denis_https--3--4--4www--1qsl--1net--4f4gop--4_.txt">x</a>')
        urls = sorted(s["url"] for s in ezpix.parse_onair_listing(page))
        self.assertEqual(urls, ["https://www.qsl.net/f0gop/", "https://www.qsl.net/f4gop/"])

    def test_la_plus_recente(self):
        st = [{"call": c, "url": f"http://x/{c}/"} for c in ("A1A", "B2B", "C3C")]
        ages = {"http://x/A1A/EZPix/image1": (900, 10), "http://x/B2B/image1": (25, 2000),
                "http://x/C3C/EZPix/image1": (40, 30)}
        with mock.patch.object(ezpix, "_age", lambda url, timeout=6: ages.get(url)):
            best = ezpix.find_latest(st)
        self.assertEqual(best[0]["call"], "B2B")
        self.assertEqual(ezpix.image_url(best[0]), "http://x/B2B/image1")      # image à la racine (F4GOP)
        ages["http://x/B2B/image1"] = (700, 5)
        with mock.patch.object(ezpix, "_age", lambda url, timeout=6: ages.get(url)):
            self.assertEqual(ezpix.find_latest(st)[0]["call"], "C3C")

    def test_receveur_pas_pris_pour_expediteur(self):
        """Signal entendu il y a 20 s : l'image déposée 5 s APRÈS (une station qui l'a reçue et la
        redépose sur son site, Digi-Sites) n'est pas retenue ; celle d'avant le signal l'est."""
        import time
        st = [{"call": "SND", "url": "http://x/snd/"}, {"call": "RCV", "url": "http://x/rcv/"}]
        ages = {"http://x/snd/image1": (35, 100), "http://x/rcv/image1": (15, 100)}
        with mock.patch.object(ezpix, "_age", lambda url, timeout=6: ages.get(url)):
            best = ezpix.find_latest(st, t_heard=time.time() - 20)
        self.assertEqual(best[0]["call"], "SND")

if __name__ == "__main__":
    unittest.main()
