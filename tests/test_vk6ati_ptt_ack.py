"""2.16 (VK6ATI) : port COM du PTT refusé un instant -> nouvel essai ; image hybride reçue en étant
connecté : pas d'ACK par radio (le Rx Ok passe déjà par Internet)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import radio  # noqa: E402


class PttRetry(unittest.TestCase):
    def cfg(self):
        return {"ptt": "RTS", "port": "COM4", "ptt_port": "COM4", "rig": "none"}

    def test_reessaie_puis_reussit(self):
        ser = mock.MagicMock()
        err = RuntimeError("COM4 est déjà utilisé par un autre programme")
        with mock.patch.object(radio.audio, "open_serial", side_effect=[err, err, ser]) as op, \
                mock.patch.object(radio.time, "sleep"):
            p = radio.Ptt(self.cfg(), None)
        self.assertIs(p.ser, ser)
        self.assertEqual(op.call_count, 3)

    def test_abandonne_apres_2_s(self):
        err = RuntimeError("COM4 est déjà utilisé par un autre programme")
        with mock.patch.object(radio.audio, "open_serial", side_effect=err) as op, \
                mock.patch.object(radio.time, "sleep"):
            with self.assertRaises(RuntimeError):
                radio.Ptt(self.cfg(), None)
        self.assertEqual(op.call_count, 6)

    def test_port_absent_pas_de_nouvel_essai(self):
        err = RuntimeError("COM9 n'existe pas")
        with mock.patch.object(radio.audio, "open_serial", side_effect=err) as op, \
                mock.patch.object(radio.time, "sleep"):
            with self.assertRaises(RuntimeError):
                radio.Ptt(self.cfg(), None)
        self.assertEqual(op.call_count, 1)


class AckHybride(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        self.d = tempfile.mkdtemp()
        self.conf = os.path.join(self.d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "en", "net_on": False,
                       "folder": self.d}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a._closing = True
        self.a.net = None
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def recv(self, hybrid, online):
        a = self.a
        a.rx_stream = object()
        a.net = mock.MagicMock(call="VK6ATI") if online else None
        a.net_ok = online
        a.ack_pending.clear()
        p = os.path.join(self.d, f"img{hybrid}{online}.png")
        Image.new("RGB", (32, 32), "blue").save(p)
        hdr = {"id": 1234 + hybrid * 2 + online, "call": "F4GOP", "size": 100, "fmt": "png", "hybrid": hybrid}
        with mock.patch.object(a, "_net_confirm"):
            try:
                a._got_image(hdr, p, p, "DATAC1")
            except Exception:
                pass
        return hdr["id"] in a.ack_pending

    def test_hybride_connecte_pas_d_ack_radio(self):
        self.assertFalse(self.recv(True, True))

    def test_hybride_sans_internet_ack_radio(self):
        self.assertTrue(self.recv(True, False))

    def test_image_radio_ack_radio(self):
        self.assertTrue(self.recv(False, True))
