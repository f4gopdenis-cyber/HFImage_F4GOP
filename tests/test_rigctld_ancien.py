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
