"""2.41 (signalé par BH2RMX) : texte en mode EasyPal (chinois, russe…), texte inclus avec l'image en
mode EasyPal ou hybride (parti juste après l'image), zone de texte vidée après l'envoi."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class Codage(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app

    def test_europeen_reste_en_cp1252(self):
        b = self.app.App._drm_text_bytes("Bonjour à tous, 73 !\nF4GOP")
        self.assertEqual(b, "Bonjour à tous, 73 !\r\nF4GOP".encode("cp1252"))   # comme EasyPal

    def test_chinois_et_russe_en_utf8(self):
        for t in ("信号弱，无法解码。", "Привет, 73!", "TO BG7LJX 中国话"):
            b = self.app.App._drm_text_bytes(t)
            self.assertNotIn(b"?", b.replace("TO BG7LJX".encode(), b""))
            self.assertEqual(b.decode("utf-8"), t)

    def test_reception(self):
        """Le fichier .txt reçu en HamDRM est relu correctement (cp1252, UTF-8, UTF-8 avec BOM)."""
        import engine
        got = []
        d = tempfile.mkdtemp()
        rx = engine.RxEngine("F4GOP", d, on_image=lambda info, p, png, m: got.append(info["text"]))
        for raw, want in ((self.app.App._drm_text_bytes("中国话 73"), "中国话 73"),
                          ("Été 73".encode("cp1252"), "Été 73"),
                          ("﻿你好".encode("utf-8"), "你好")):
            rx._save_drm({"data": raw, "callsign": "BH2RMX", "name": "BH2RMX_texte.txt", "mode": "B", "snr": 5})
            self.assertEqual(got[-1], want)


class AppTexte(unittest.TestCase):
    def setUp(self):
        import gc
        import json
        from unittest import mock
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.appmod = app
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "BH2RMX", "licence_ok": "1.0", "lang": "fr"}, f)
        gc.collect()
        self.p = mock.patch.object(app, "CONF_PATH", conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.jobs = []
        a = self.a

        def fake_start(job, quiet=False):
            self.jobs.append(job)
            a.tx_busy = True
            return True
        a._start_job = fake_start

    def tearDown(self):
        self.a.destroy()
        self.p.stop()

    def test_zone_videe_apres_envoi(self):
        a = self.a
        a.txt_msg.insert("1.0", "TO BG7LJX 73")
        a.send_text()
        self.assertEqual(len(self.jobs), 1)
        self.assertEqual(self.jobs[0]["kind"], "text")
        self.assertEqual(a.txt_msg.get("1.0", "end").strip(), "")

    def test_zone_gardee_si_echec(self):
        a = self.a
        a._start_job = lambda job, quiet=False: False
        a.txt_msg.insert("1.0", "pas parti")
        a.send_text()
        self.assertEqual(a.txt_msg.get("1.0", "end").strip(), "pas parti")

    def test_texte_inclus_hybride_apres_l_image(self):
        a = self.a
        a.txt_msg.insert("1.0", "中国话")
        a.v_txtinc.set(True)
        a.v_hyb.set(True)
        a._hyb_cfg = lambda: {"host": "ftp.example.org", "url": "https://example.org/", "dir": ""}
        job = self.appmod.HybridJob(b"\xff\xd8\xff", "jpeg", "BH2RMX")
        self.assertTrue(a.transmit(tx=job, quiet=True))
        self.assertEqual(self.jobs[-1]["kind"], "hybrid")
        a.stop_tx.clear()
        a._tx_done(False)                                    # fin de l'image
        import time
        end = time.time() + 2
        while time.time() < end and len(self.jobs) < 2:
            a.update()
            time.sleep(0.02)
        self.assertEqual(len(self.jobs), 2)                  # puis le texte, tout seul
        self.assertEqual(self.jobs[-1]["kind"], "text")
        self.assertEqual(a.txt_msg.get("1.0", "end").strip(), "中国话")   # gardé pour l'image suivante

    def test_stop_annule_le_texte(self):
        a = self.a
        a.txt_msg.insert("1.0", "73")
        a.v_txtinc.set(True)
        a.v_hyb.set(True)
        a._hyb_cfg = lambda: {"host": "ftp.example.org", "url": "https://example.org/", "dir": ""}
        a.transmit(tx=self.appmod.HybridJob(b"\xff\xd8\xff", "jpeg", "BH2RMX"), quiet=True)
        a.stop_tx.set()                                      # STOP pendant l'image
        a._tx_done(False)
        a.update()
        import time
        time.sleep(1.0)
        a.update()
        self.assertEqual(len(self.jobs), 1)


if __name__ == "__main__":
    unittest.main()
