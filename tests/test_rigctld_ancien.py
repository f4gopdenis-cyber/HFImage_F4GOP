"""Version 1.73 : rigctld des distributions Linux qui répond à « f » par la fréquence ET le VFO
(F4EEI : fréquence non lue en « Hamlib NET rigctl », alors que le PTT marchait)."""
import os
import socket
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import radio  # noqa: E402


class RigctldAncien(unittest.TestCase):
    def setUp(self):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def tearDown(self):
        self.srv.close()

    def serve(self):
        c, _ = self.srv.accept()
        f = c.makefile("rwb")
        for line in f:
            cmd = line.decode().strip()
            f.write({"f": b"7058000\nVFOA\n", "m": b"LSB\n2400\n"}.get(cmd, b"RPRT 0\n"))
            f.flush()
        c.close()

    def test_reponses_pas_decalees(self):
        c = dict(radio.DEFAULTS, rig="netrigctl", host=f"127.0.0.1:{self.port}")
        r = radio.make_rig(c)
        try:
            for _ in range(4):
                self.assertEqual(r.freq(), 7058000)
                self.assertEqual(r.mode(), "LSB")
            r.ptt(True)
            r.ptt(False)
            self.assertEqual(r.freq(), 7058000)
        finally:
            r.close()


if __name__ == "__main__":
    unittest.main()


class RigctldVfo(unittest.TestCase):
    """1.75 : rigctld lancé avec --vfo (-o) : chaque commande doit porter le VFO (« f currVFO »)."""

    def setUp(self):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        self.got = []
        threading.Thread(target=self.serve, daemon=True).start()

    def tearDown(self):
        self.srv.close()

    def serve(self):
        c, _ = self.srv.accept()
        f = c.makefile("rwb")
        for line in f:
            cmd = line.decode().strip()
            self.got.append(cmd)
            if cmd == "\\chk_vfo":
                f.write(b"1\n")
            elif cmd == "f currVFO":
                f.write(b"7058000\n")
            elif cmd == "m currVFO":
                f.write(b"PKTLSB\n2400\n")
            elif cmd.startswith(("T currVFO", "F currVFO", "M currVFO")):
                f.write(b"RPRT 0\n")
            else:
                f.write(b"RPRT -1\n")
            f.flush()
        c.close()

    def test_vfo_ajoute(self):
        r = radio.make_rig(dict(radio.DEFAULTS, rig="netrigctl", host=f"127.0.0.1:{self.port}"))
        try:
            self.assertEqual(r.freq(), 7058000)
            self.assertEqual(r.mode(), "PKTLSB")
            r.ptt(True)
            r.set_freq(7060000)
        finally:
            r.close()
        self.assertIn("T currVFO 3", self.got)
        self.assertIn("F currVFO 7060000", self.got)

    def test_reponse_gardee_pour_le_journal(self):
        r = radio.make_rig(dict(radio.DEFAULTS, rig="netrigctl", host=f"127.0.0.1:{self.port}"))
        try:
            r.vfo_mode = False                       # force « f » seul : le faux serveur répond RPRT -1
            self.assertIsNone(r.freq())
            self.assertEqual(r.last_reply, "RPRT -1")
        finally:
            r.close()


class RigctldReveil(unittest.TestCase):
    """1.77 : rigctld répond « RPRT -1 » à « f » tant qu'on ne lui a pas demandé le VFO (F4EEI)."""

    def setUp(self):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def tearDown(self):
        self.srv.close()

    def serve(self):
        c, _ = self.srv.accept()
        f = c.makefile("rwb")
        awake = False
        for line in f:
            cmd = line.decode().strip()
            if cmd == "v":
                awake = True
                f.write(b"VFOA\n")
            elif cmd == "f":
                f.write(b"7058000\n" if awake else b"RPRT -1\n")
            elif cmd == "m":
                f.write(b"LSB\n2400\n")
            elif cmd == "\\chk_vfo":
                f.write(b"0\n")
            else:
                f.write(b"RPRT 0\n")
            f.flush()
        c.close()

    def test_reveil_par_v(self):
        r = radio.make_rig(dict(radio.DEFAULTS, rig="netrigctl", host=f"127.0.0.1:{self.port}"))
        try:
            self.assertEqual(r.freq(), 7058000)
            self.assertEqual(r.freq(), 7058000)
            self.assertEqual(r.mode(), "LSB")
        finally:
            r.close()
